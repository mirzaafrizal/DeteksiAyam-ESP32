import logging
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import ConnectionFailure, WriteError, WriteConcernError, OperationFailure
from motor.motor_asyncio import AsyncIOMotorDatabase

from schemas.detection_log import DetectionLogCreate, DetectionLogResponse
from utils.cache import cache

logger = logging.getLogger(__name__)

COLLECTION_NAME = "detection_logs"
LOGS_CACHE_KEY = "logs_cache"

# Collation for case-insensitive posture_label filtering
_CASE_INSENSITIVE_COLLATION = {"locale": "en", "strength": 2}


def _serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to a JSON-serialisable dict with string _id."""
    doc = dict(doc)
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


class DetectionLogService:
    """Service layer for CRUD operations on the detection_logs MongoDB collection."""

    # ------------------------------------------------------------------
    # create_log
    # ------------------------------------------------------------------

    async def create_log(
        self,
        db: AsyncIOMotorDatabase,
        log_data: DetectionLogCreate,
    ) -> str:
        """
        Insert a new Detection_Log document into MongoDB.

        Parameters
        ----------
        db:
            Motor async database instance injected by FastAPI dependency.
        log_data:
            Validated Pydantic model containing all required fields.

        Returns
        -------
        str
            The newly-inserted document's ObjectId as a hex string.

        Raises
        ------
        HTTPException(503)
            When MongoDB is unreachable (ConnectionFailure).
        HTTPException(500)
            When the insert fails due to a write-level error.
        """
        document = {
            "timestamp": log_data.timestamp,
            # Dibuat lebih aman dengan hasattr agar tidak crash jika dikirim string biasa
            "posture_label": log_data.posture_label.value if hasattr(log_data.posture_label, 'value') else log_data.posture_label,
            "confidence_score": log_data.confidence_score,
            "image_url": log_data.image_url,
            # 👇 KODE BARU: Wajib ditulis biar jumlah ayam tersimpan ke Database! 👇
            "jumlah_ayam": getattr(log_data, "jumlah_ayam", 0),
            # ─── 3 BARIS TAMBAHAN UNTUK LATENCY (BUKTI DOSEN) ───
            "waktu_terima_esp": getattr(log_data, "waktu_terima_esp", ""),
            "waktu_mulai_yolo": getattr(log_data, "waktu_mulai_yolo", ""),
            "durasi_total_detik": getattr(log_data, "durasi_total_detik", 0.0),
            # ────────────────────────────────────────────────────
        }

        try:
            collection = db[COLLECTION_NAME]
            result = await collection.insert_one(document)
            log_id = str(result.inserted_id)
            logger.info("Detection log inserted: %s", log_id)
            return log_id

        except ConnectionFailure as exc:
            logger.error("MongoDB connection failure during create_log: %s", exc)
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "DB_UNAVAILABLE",
                    "message": (
                        "Koneksi ke MongoDB tidak tersedia. "
                        "Silakan coba kembali beberapa saat."
                    ),
                    "status_code": 503,
                },
            ) from exc

        except (WriteError, WriteConcernError, OperationFailure) as exc:
            logger.error("MongoDB write error during create_log: %s", exc)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "DB_WRITE_ERROR",
                    "message": (
                        "Terjadi kesalahan saat menyimpan data ke database. "
                        "Silakan coba kembali."
                    ),
                    "status_code": 500,
                },
            ) from exc

    # ------------------------------------------------------------------
    # get_logs
    # ------------------------------------------------------------------

    async def get_logs(
        self,
        db: AsyncIOMotorDatabase,
        limit: int = 10000,  # <-- Sesuai yang Kakak set
        posture_label: Optional[str] = None,
    ) -> list[dict]:
        """
        Retrieve Detection_Log documents sorted by timestamp descending.

        Parameters
        ----------
        db:
            Motor async database instance injected by FastAPI dependency.
        limit:
            Maximum number of documents to return (1–500, default 100).
        posture_label:
            Optional case-insensitive filter on posture_label.

        Returns
        -------
        list[dict]
            List of serialised Detection_Log documents (``_id`` as string).
            Falls back to the in-memory cache when MongoDB is unreachable.

        Raises
        ------
        HTTPException(503)
            When MongoDB is unreachable and no cache is available.
        """
        query: dict = {}
        if posture_label is not None:
            query["posture_label"] = posture_label

        try:
            collection = db[COLLECTION_NAME]

            cursor = (
                collection
                .find(query, collation=_CASE_INSENSITIVE_COLLATION)
                .sort("timestamp", -1)
                .limit(limit)
            )

            docs = [_serialize_doc(doc) async for doc in cursor]

            # Refresh the cache only when no filter is applied so that the
            # cached data represents the full unfiltered result set.
            if posture_label is None:
                cache.set(LOGS_CACHE_KEY, docs)
                logger.debug("Cache updated with %d detection logs.", len(docs))

            return docs

        except ConnectionFailure as exc:
            logger.error("MongoDB connection failure during get_logs: %s", exc)

            cached = cache.get(LOGS_CACHE_KEY)
            if cached is not None:
                logger.warning(
                    "MongoDB unavailable — returning %d cached detection logs.",
                    len(cached),
                )
                return cached

            raise HTTPException(
                status_code=503,
                detail={
                    "error": "DB_UNAVAILABLE",
                    "message": (
                        "Koneksi ke MongoDB tidak tersedia dan tidak ada data "
                        "cache yang tersimpan."
                    ),
                    "status_code": 503,
                },
            ) from exc