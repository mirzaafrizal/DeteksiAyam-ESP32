"""
main.py — FastAPI application factory.

Bertanggung jawab atas:
  - Lifespan handler (startup + shutdown)
  - CORS middleware
  - Global exception handler (Requirements 8.1–8.4, 8.6)
  - Pendaftaran router upload dan logs
"""
import logging
import time # Pastikan ini ditambahkan di kumpulan import paling atas
from contextlib import asynccontextmanager

from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from dependencies.database import close_db, connect_db, get_db
from routers import logs, upload
from scripts.create_indexes import create_indexes

logger = logging.getLogger(__name__)


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:
      1. Validasi env vars wajib via get_settings() — raises ValueError jika hilang.
      2. Buat koneksi async ke MongoDB via Motor.
      3. Simpan database_name ke app.state agar bisa diakses oleh dependency get_db().

    Shutdown:
      1. Tutup koneksi MongoDB.
    """
    # --- Startup ---
    settings = get_settings()  # raises ValueError (MISSING_CONFIG) jika env var hilang
    await connect_db(settings)
    app.state.database_name = settings.DATABASE_NAME

    # Buat MongoDB indexes sekali saat startup (idempotent)
    from dependencies.database import _client
    db = _client[settings.DATABASE_NAME]
    await create_indexes(db)

    logger.info(
        "Startup selesai. Terhubung ke database '%s'.", settings.DATABASE_NAME
    )

    yield

    # --- Shutdown ---
    await close_db()
    logger.info("Shutdown selesai. Koneksi database ditutup.")


# ─── App Factory ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Chicken Posture Detection API",
    description=(
        "API untuk deteksi postur ayam abnormal menggunakan YOLOv8. "
        "Menerima gambar dari ESP32-CAM, menjalankan inferensi, dan "
        "menyimpan hasil ke MongoDB."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Middleware ───────────────────────────────────────────────────────────────

# Requirement 8.3 & 8.4: izinkan semua cross-origin request (termasuk preflight OPTIONS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global Exception Handler ────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Tangani semua exception yang tidak ditangani oleh handler lain.

    Requirement 8.2: selalu kembalikan JSON dengan Content-Type application/json.
    """
    logger.error(
        "Unhandled exception pada %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "Terjadi kesalahan internal server.",
            "status_code": 500,
        },
    )

# Membuka akses folder 'images' ke publik
app.mount("/images", StaticFiles(directory="images"), name="images")

# --- KODE BARU: SISTEM HEARTBEAT ESP32 ---
ESP32_LAST_SEEN = 0  # Menyimpan waktu terakhir ESP32 absen

@app.get("/api/esp32/ping")
def ping_esp32():
    """Endpoint ini nanti akan diakses ESP32 setiap 3 detik untuk 'absen'"""
    global ESP32_LAST_SEEN
    ESP32_LAST_SEEN = time.time()
    return {"status": "ok", "message": "ESP32 is alive"}

@app.get("/api/esp32/status")
def get_esp32_status():
    """Website akan mengecek ini untuk tahu apakah ESP32 masih online"""
    # Dianggap ONLINE jika absen terakhir kurang dari 10 detik yang lalu
    is_online = (time.time() - ESP32_LAST_SEEN) < 10
    return {"online": is_online}
# ----------------------------------------

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(logs.router)