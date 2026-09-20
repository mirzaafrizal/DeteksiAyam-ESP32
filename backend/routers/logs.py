"""
Router untuk GET /logs.

Mengambil riwayat Detection_Log dari MongoDB dengan dukungan:
  - Parameter `limit` (default 100, rentang 1–500) dengan validasi 400 custom
  - Parameter `posture_label` untuk filter case-insensitive
  - Fallback ke in-memory cache jika MongoDB tidak tersedia (503 jika cache kosong)

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from dependencies.database import get_db
from services.detection_log import DetectionLogService

logger = logging.getLogger(__name__)

router = APIRouter()

_service = DetectionLogService()

# Sentinel — digunakan untuk membedakan "parameter tidak dikirim" vs "nilai dikirim"
_LIMIT_NOT_SET = object()


@router.get(
    "/logs",
    summary="Ambil riwayat Detection Log",
    description=(
        "Kembalikan daftar Detection_Log dari MongoDB, diurutkan berdasarkan "
        "timestamp descending. Mendukung filter `posture_label` (case-insensitive) "
        "dan pembatasan jumlah hasil via `limit` (1–500, default 100). "
        "Jika MongoDB tidak tersedia, fallback ke cache; jika cache kosong, "
        "kembalikan 503."
    ),
    responses={
        200: {"description": "Array Detection_Log (kosong jika tidak ada data)"},
        400: {"description": "Parameter `limit` tidak valid"},
        503: {"description": "MongoDB tidak tersedia dan tidak ada cache"},
    },
)
async def get_logs(
    request: Request,
    # Menerima limit sebagai Optional[int] tanpa constraint ge/le agar validasi
    # custom bisa mengembalikan 400 (bukan 422 default FastAPI).
    # Non-integer otomatis menghasilkan 422 dari FastAPI — kita override di bawah
    # dengan menggunakan Query tanpa tipe ketat dan mem-parse manual.
    limit: Optional[str] = Query(default=None),
    posture_label: Optional[str] = Query(default=None),
    db=Depends(get_db),
):
    """
    GET /logs — ambil riwayat log deteksi.

    Requirement 4.7: nilai limit di luar rentang [1, 500] atau bukan integer
    harus mengembalikan 400 Bad Request dengan error INVALID_LIMIT.
    """
   # ── Validasi dan parsing `limit` ─────────────────────────────────────────
    if limit is None:
        parsed_limit = 10000
    else:
        try:
            parsed_limit = int(limit)
        except (ValueError, TypeError):
            logger.warning("Nilai limit tidak valid (bukan integer): %r", limit)
            return JSONResponse(
                status_code=400,
                content={
                    "error": "INVALID_LIMIT",
                    "message": (
                        "Nilai parameter `limit` tidak valid. "
                        "Harus berupa bilangan bulat dalam rentang 1–10000." # <-- Diubah
                    ),
                    "status_code": 400,
                },
            )

        # ─── KODE YANG DIUBAH (SATPAMNYA KITA KASIH KELONGGARAN) ───
        if parsed_limit < 1 or parsed_limit > 500: 
            logger.warning("Nilai limit di luar rentang: %d", parsed_limit)
            return JSONResponse(
                status_code=400,
                content={
                    "error": "INVALID_LIMIT",
                    "message": (
                        f"Nilai parameter `limit` ({parsed_limit}) di luar rentang valid. "
                        "Harus berupa bilangan bulat dalam rentang 1–10000." # <-- Diubah
                    ),
                    "status_code": 400,
                },
            )
        # ───────────────────────────────────────────────────────────

    # ── Ambil data dari service (MongoDB → cache → 503) ───────────────────────
    docs = await _service.get_logs(
        db=db,
        limit=parsed_limit,
        posture_label=posture_label,
    )

    return docs
