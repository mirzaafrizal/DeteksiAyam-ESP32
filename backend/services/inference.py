"""
InferenceService — menjalankan inferensi postur ayam terhadap bytes gambar.

Perilaku otomatis:
- Jika backend/models/best.pt ADA  → pakai YOLO real
- Jika best.pt TIDAK ADA           → fallback ke mock (random label+confidence)

Sehingga tidak perlu mengubah kode apapun setelah training selesai —
cukup taruh best.pt di backend/models/ lalu restart backend.
"""

import asyncio
import io
import logging
import random
import tempfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from schemas.detection_log import PostureLabel

logger = logging.getLogger(__name__)

# --- KAMUS TRANSLASI LABEL ---
LABEL_MAP = {
    "Healthy": "Normal",
    "Chicken": "Normal",
    "chicken": "Normal",
    "hen": "Normal",
    "agresif": "Normal",
    "makan": "Duduk Tidak Tegak",
    "Sick": "Telungkup"
}
# -----------------------------------

# Label postur yang valid — sesuai dengan PostureLabel enum
_POSTURE_LABELS: list[PostureLabel] = [
    PostureLabel.NORMAL,
    PostureLabel.DUDUK_TIDAK_TEGAK,
    PostureLabel.TELUNGKUP,
]

# Rentang confidence score untuk mock
_CONFIDENCE_MIN = 0.50
_CONFIDENCE_MAX = 0.99

# Batas waktu inferensi dalam detik
_INFERENCE_TIMEOUT_SECONDS = 30

# Path model — relatif terhadap file ini (backend/services/ → backend/models/)
_MODEL_PATH = Path(__file__).parent.parent / "models" / "best.pt"


def _load_yolo_model():
    """
    Muat model YOLO dari best.pt jika tersedia.
    Kembalikan None jika file tidak ada atau ultralytics tidak terinstall.
    """
    if not _MODEL_PATH.exists():
        logger.info(
            "best.pt tidak ditemukan di %s — menggunakan mock inference.", _MODEL_PATH
        )
        return None

    try:
        from ultralytics import YOLO  # noqa: PLC0415
        model = YOLO(str(_MODEL_PATH))
        logger.info("Model YOLO berhasil dimuat dari %s", _MODEL_PATH)
        return model
    except ImportError:
        logger.warning(
            "ultralytics tidak terinstall — menggunakan mock inference. "
            "Install dengan: pip install ultralytics"
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error("Gagal memuat model YOLO: %s — fallback ke mock.", exc)
        return None


# Muat model sekali saat module diimport (singleton)
_yolo_model = _load_yolo_model()


class InferenceResult:
    """Hasil inferensi postur ayam dari satu gambar."""

    # 👇 UBAH DISINI: Tambahkan jumlah_ayam ke dalam constructor
    def __init__(self, posture_label: PostureLabel, confidence_score: float, annotated_bytes: bytes = None, jumlah_ayam: int = 0) -> None:
        self.posture_label = posture_label
        self.confidence_score = round(confidence_score, 4)
        self.annotated_bytes = annotated_bytes
        self.jumlah_ayam = jumlah_ayam  # <--- Simpan variabelnya

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"InferenceResult(posture_label={self.posture_label!r}, "
            f"confidence_score={self.confidence_score}, "
            f"jumlah_ayam={self.jumlah_ayam})"
        )


class InferenceService:
    """
    Service yang mengekspos method predict() untuk mengklasifikasikan postur ayam.
    """

    async def predict(self, image_bytes: bytes) -> InferenceResult:
        # Validasi integritas gambar
        self._validate_image(image_bytes)

        # Pilih inferensi: YOLO real atau mock
        if _yolo_model is not None:
            coro = self._run_model_inference(image_bytes)
        else:
            coro = self._run_mock_inference(image_bytes)

        try:
            result = await asyncio.wait_for(coro, timeout=_INFERENCE_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as exc:
            logger.error(
                "Inferensi melebihi batas waktu %d detik.", _INFERENCE_TIMEOUT_SECONDS
            )
            raise TimeoutError(
                f"Proses inferensi melebihi batas waktu {_INFERENCE_TIMEOUT_SECONDS} detik."
            ) from exc

        logger.debug(
            "Inferensi selesai: label=%s, score=%.4f, jumlah=%d",
            result.posture_label.value if hasattr(result.posture_label, 'value') else result.posture_label,
            result.confidence_score,
            result.jumlah_ayam
        )
        return result

    # ── Private helpers ──────────────────────────────────────────────────────

    def _validate_image(self, image_bytes: bytes) -> None:
        """Verifikasi bahwa image_bytes adalah gambar yang valid menggunakan Pillow."""
        if not image_bytes:
            raise ValueError("Bytes gambar kosong.")

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img.verify()
        except UnidentifiedImageError as exc:
            logger.warning("Gambar tidak dapat diidentifikasi: %s", exc)
            raise ValueError(
                "Gambar tidak dapat diidentifikasi. File mungkin bukan gambar yang valid."
            ) from exc
        except (OSError, SyntaxError) as exc:
            logger.warning("Gambar rusak: %s", exc)
            raise ValueError(f"Gambar rusak atau tidak dapat dibaca: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            logger.warning("Validasi gambar gagal: %s", exc)
            raise ValueError(f"Validasi gambar gagal: {exc}") from exc

    async def _run_model_inference(self, image_bytes: bytes) -> InferenceResult:
        tmp_path = None
        try:
            # Tulis ke file sementara
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name

            # Jalankan YOLO predict di thread (blocking → non-blocking)
            results = await asyncio.to_thread(
                _yolo_model.predict, tmp_path, verbose=False
            )

            # --- KODE BARU YANG LEBIH AMAN: HACK SAAT MENGGAMBAR ---
            if hasattr(results[0], 'names'):
                indo_names = {}
                for k, v in results[0].names.items():
                    indo_names[k] = LABEL_MAP.get(v, "Normal")
                results[0].names = indo_names
            # -------------------------------------------------------

            # YOLO akan otomatis menggambar kotak dengan label yang sudah diterjemahkan
            results[0].save(filename=tmp_path)
            
            # Baca kembali file yang sudah ada kotaknya menjadi bytes
            with open(tmp_path, "rb") as f:
                annotated_image_bytes = f.read()

            boxes = results[0].boxes
            if boxes is None or len(boxes) == 0:
                logger.warning("YOLO tidak mendeteksi objek dalam gambar.")
                raise ValueError(
                    "Model tidak menemukan objek ayam dalam gambar. "
                    "Pastikan gambar berisi ayam yang jelas."
                )

            # 👇 KODE BARU: HITUNG JUMLAH KOTAK (AYAM) 👇
            total_ayam = len(boxes)

            # --- LOGIKA BARU: PRIORITASKAN AYAM SAKIT (MULTI-OBJECT) ---
            # Kita buat urutan prioritas bahaya: Telungkup (3) > Duduk Tidak Tegak (2) > Normal (1)
            priority_map = {"Telungkup": 3, "Duduk Tidak Tegak": 2, "Normal": 1}
            
            final_class_id = 0
            final_confidence = 0.0
            highest_priority = 0

            # Cek satu per satu semua ayam yang terdeteksi di gambar
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                label = results[0].names[cls_id]
                
                current_priority = priority_map.get(label, 1)
                
                # Jika ketemu ayam yang kondisinya LEBIH BAHAYA, catat ayam ini!
                # Atau jika bahayanya sama, tapi AI lebih yakin (confidence tinggi), catat yang ini!
                if current_priority > highest_priority or (current_priority == highest_priority and conf > final_confidence):
                    highest_priority = current_priority
                    final_class_id = cls_id
                    final_confidence = conf

            # Hasil akhirnya adalah label ayam yang paling berbahaya di foto tersebut
            label_name = results[0].names[final_class_id]
            confidence = final_confidence
            # -------------------------------------------------------------
            
            posture_label = PostureLabel(label_name) if hasattr(PostureLabel, label_name.upper().replace(" ", "_")) else label_name
            
            return InferenceResult(
                posture_label=posture_label,
                confidence_score=confidence,
                annotated_bytes=annotated_image_bytes,
                # 👇 KODE BARU: KIRIM JUMLAH AYAM KE HASIL INFERENSI 👇
                jumlah_ayam=total_ayam,
            )

        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    async def _run_mock_inference(self, image_bytes: bytes) -> InferenceResult:  # noqa: ARG002
        await asyncio.sleep(0.1)

        posture_label: PostureLabel = random.choice(_POSTURE_LABELS)
        confidence_score: float = random.uniform(_CONFIDENCE_MIN, _CONFIDENCE_MAX)
        jumlah_ayam: int = random.randint(1, 10) # Mock jumlah ayam random

        return InferenceResult(
            posture_label=posture_label,
            confidence_score=confidence_score,
            jumlah_ayam=jumlah_ayam,
        )