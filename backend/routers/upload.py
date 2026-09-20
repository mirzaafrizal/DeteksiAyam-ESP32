"""
Router untuk POST /upload.

Alur:
  1. Terima UploadFile dari multipart/form-data
  2. Validasi via ImageValidator.validate()
  3. Simpan gambar ke IMAGES_DIR dengan nama berbasis timestamp
  4. Jalankan InferenceService.predict()
  5. (BARU) Anulir dan Hapus Foto jika Confidence < 40% atau tidak ada ayam.
  6. Simpan DetectionLog via DetectionLogService.create_log()
  7. Kirim sinyal MQTT ke RabbitMQ jika postur bahaya (Telungkup / Duduk Tidak Tegak)
  8. Kembalikan UploadResponse 200 OK
"""

import logging
import os
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

# --- KODE BARU: Import library Paho MQTT ---
import paho.mqtt.publish as mqtt_publish

from config import get_settings, Settings
from dependencies.database import get_db
from schemas.detection_log import DetectionLogCreate
from schemas.responses import UploadResponse
from services.detection_log import DetectionLogService
from services.inference import InferenceService
from utils.image_validator import ImageValidator

logger = logging.getLogger(__name__)

router = APIRouter()

_image_validator = ImageValidator()
_inference_service = InferenceService()
_detection_log_service = DetectionLogService()

# ─── VARIABEL GLOBAL PEMBATAS 15 DETIK ───
last_log_time = 0.0
LOG_INTERVAL = 14.0

# ─── FUNGSI MEMAKSA WAKTU WIB (UTC+7 DENGAN OFFSET EKSPLISIT) ───
WIB = timezone(timedelta(hours=7))

def get_wib_now() -> datetime:
    return datetime.now(WIB)
# ──────────────────────────────────────────────────────────────

def _build_timestamp_filename(ext: str) -> tuple[str, datetime]:
    now = get_wib_now() # Gunakan waktu WIB
    ts_str = now.strftime("%Y-%m-%dT%H-%M-%S-") + f"{now.microsecond // 1000:03d}"
    return ts_str, now


def _get_image_extension(content_type: str) -> str:
    mapping = {
        "image/jpeg": "jpg",
        "image/png": "png",
    }
    return mapping.get((content_type or "").lower().split(";")[0].strip(), "jpg")


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=200,
    summary="Upload gambar untuk deteksi postur ayam",
)
async def upload_image(
    file: UploadFile = File(..., description="File gambar JPEG atau PNG, maks 5 MB"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    global last_log_time

    # ── 1. Catat Waktu Terima Gambar dari ESP ──
    t_received = time.time()
    dt_received = get_wib_now().strftime("%H:%M:%S.%f")[:-3]

    # ── 1. Validasi file ────────
    image_bytes: bytes = await _image_validator.validate(file)

    # ── 2. Tentukan nama file dan simpan ────────
    ext = _get_image_extension(file.content_type)
    filename_base, timestamp_dt = _build_timestamp_filename(ext)
    filename = f"{filename_base}Z.{ext}"

    images_dir = settings.IMAGES_DIR
    os.makedirs(images_dir, exist_ok=True)

    image_path = os.path.join(images_dir, filename)
    image_url = f"/images/{filename}"

    try:
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        logger.info("Gambar disimpan sementara: %s", image_path)
    except OSError as exc:
        logger.error("Gagal menyimpan gambar ke disk: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "STORAGE_ERROR",
                "message": "Gagal menyimpan gambar ke server.",
                "status_code": 500,
            },
        )

    # ── 3. Jalankan inferensi YOLO ────────
    # Siapkan nilai bawaan (default) jika gambar kosong / tidak ada ayam
    posture_val = "Tidak Ada Ayam" 
    conf_val = 0.0
    is_valid_detection = False
    
    frame_to_display = image_bytes 
    dt_yolo_start = ""
    total_process_time = 0.0

    try:
        t_yolo_start = time.time()
        dt_yolo_start = get_wib_now().strftime("%H:%M:%S.%f")[:-3]

        inference_result = await _inference_service.predict(image_bytes)
        
        t_yolo_end = time.time()
        total_process_time = round((t_yolo_end - t_received), 3)

        # Update frame untuk Livestream Frontend
        if inference_result.annotated_bytes:
            frame_to_display = inference_result.annotated_bytes

        # Jika AI sukses ngebaca ayam, pakai hasil aslinya
        posture_val = inference_result.posture_label
        conf_val = inference_result.confidence_score
        
        # 👇 TANGKAP JUMLAH AYAM DARI YOLO 👇
        total_ayam_terdeteksi = inference_result.jumlah_ayam

        # ─── KODE BARU: ANULIR CONFIDENCE DI BAWAH 65% ───
        if conf_val < 0.65:
            logger.info("Deteksi %.1f%% (di bawah 65%%). Gambar halusinasi dianulir dan dibuang.", conf_val * 100)
            posture_val = "Tidak Ada Ayam (Confidence Rendah)"
            total_ayam_terdeteksi = 0 # Anulir jumlah ayamnya
        else:
            is_valid_detection = True
            if inference_result.annotated_bytes:
                with open(image_path, "wb") as f:
                    f.write(inference_result.annotated_bytes)
        # ─────────────────────────────────────────────────

    except ValueError as exc:
        # ─── KODE BARU: JIKA FOTO KOSONG (TEMBOK), LANGSUNG HAPUS & JANGAN SIMPAN! ───
        t_yolo_end = time.time()
        total_process_time = round((t_yolo_end - t_received), 3)
        logger.warning("Tidak ada ayam (foto tembok). Gambar dibuang: %s", exc)
        posture_val = "Tidak Ada Ayam"
        total_ayam_terdeteksi = 0 # Tidak ada ayam = 0 ekor

    except TimeoutError as exc:
        _cleanup_image(image_path)
        logger.error("Inferensi timeout: %s", exc)
        return JSONResponse(status_code=504, content={"error": "INFERENCE_TIMEOUT", "status_code": 504})

    # ─── UPDATE GAMBAR UNTUK LIVESTREAM FRONTEND ───
    try:
        latest_live_path = os.path.join(images_dir, "latest_frame.jpg")
        with open(latest_live_path, "wb") as f_live:
            f_live.write(frame_to_display)
    except Exception as e:
        logger.error(f"Gagal menyimpan latest_frame: {e}")
    # ───────────────────────────────────────────────

    # Cek apakah posture_val bentuknya Enum (dari AI) atau String biasa (dari default)
    label_string = posture_val.value if hasattr(posture_val, 'value') else posture_val

    # ── 4. GERBANG PENCATATAN 15 DETIK KE MONGODB ────────
    current_time = time.time()
    log_id = None

    if (current_time - last_log_time) >= LOG_INTERVAL:
        # KODE BARU: RESET TIMER DULUAN DI SINI! Biar nggak stuck!
        last_log_time = current_time
        
        log_data = DetectionLogCreate(
            timestamp=timestamp_dt,
            posture_label=label_string,
            confidence_score=conf_val,
            image_url=image_url if is_valid_detection else "",
            # 👇 MASUKKAN KE DATABASE 👇
            jumlah_ayam=total_ayam_terdeteksi,
            waktu_terima_esp=dt_received,
            waktu_mulai_yolo=dt_yolo_start,
            durasi_total_detik=total_process_time
        )

        try:
            log_id = await _detection_log_service.create_log(db=db, log_data=log_data)
            logger.info("✅ [LOG 15 DETIK DISIMPAN] log_id=%s, label=%s, latency=%ss, jumlah=%s ekor", log_id, label_string, total_process_time, total_ayam_terdeteksi)
        except Exception as exc:
            logger.error("Gagal menyimpan log 15 detik ke DB: %s", exc)
            pass

    # ── 5. Hapus Gambar Fisik Jika Kosong & Return JSON ────────
    if not is_valid_detection:
        _cleanup_image(image_path) # Bersihkan foto dari hardisk
        return JSONResponse(
            status_code=200, # Tetap 200 agar ESP32 tidak ngambek
            content={"status": "ignored", "message": "Tidak ada ayam / confidence rendah."}
        )

    # ── 6. KIRIM SINYAL MQTT KE RABBITMQ ──────────────────────────
    if label_string in ["Telungkup", "Duduk Tidak Tegak"]:
        try:
            mqtt_publish.single(
                topic="kandang/buzzer",
                payload="ON",
                hostname="localhost",
                port=1883,
                client_id="backend_fastapi_publisher"
            )
            logger.info("🚨 BERHASIL: Sinyal MQTT 'ON' dikirim!")
        except Exception as e:
            logger.error("❌ GAGAL: Tidak dapat mengirim sinyal MQTT. Error: %s", e)

    # ── 7. Kembalikan Response ke Frontend ────────
    return UploadResponse(
        status="success",
        posture_label=label_string,
        confidence_score=conf_val,
        image_url=image_url,
        log_id=str(log_id) if log_id else "", # Fix error 500
        # 👇 KIRIM KE FRONTEND 👇
        jumlah_ayam=total_ayam_terdeteksi
    )

def _cleanup_image(image_path: str) -> None:
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
    except OSError as exc:
        logger.warning("Gagal menghapus file gambar: %s", exc)