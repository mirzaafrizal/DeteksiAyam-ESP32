"""
create_indexes.py — Script setup MongoDB indexes untuk collection detection_logs.

Indexes yang dibuat:
  1. { timestamp: -1 }
       → mempercepat sorting descending pada /logs (Requirement 4.2)
  2. { posture_label: 1 } dengan collation { locale: "en", strength: 2 }
       → mempercepat filter case-insensitive pada /logs (Requirement 4.4)
  3. { posture_label: 1, timestamp: -1 } compound
       → mempercepat query gabungan filter + sort (Requirement 4.2 + 4.4)

Penggunaan standalone:
  cd backend
  python -m scripts.create_indexes

Penggunaan dari main.py (lifespan startup):
  from scripts.create_indexes import create_indexes
  await create_indexes(db)
"""
import asyncio
import logging
import os
import sys

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

logger = logging.getLogger(__name__)

COLLECTION_NAME = "detection_logs"


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Buat tiga indexes pada collection detection_logs.

    Menggunakan create_indexes() dengan daftar IndexModel agar semua index
    dibuat dalam satu round-trip ke MongoDB. Operasi ini idempotent — MongoDB
    tidak akan membuat duplikat jika index dengan nama/spesifikasi yang sama
    sudah ada.

    Args:
        db: Instance AsyncIOMotorDatabase yang sudah terkoneksi.
    """
    collection = db[COLLECTION_NAME]

    indexes = [
        # Index 1: sorting descending berdasarkan timestamp
        IndexModel(
            [("timestamp", DESCENDING)],
            name="idx_timestamp_desc",
        ),
        # Index 2: filter posture_label case-insensitive
        # collation strength=2 → hanya membedakan base characters,
        # mengabaikan perbedaan huruf besar/kecil (a == A)
        IndexModel(
            [("posture_label", ASCENDING)],
            name="idx_posture_label_ci",
            collation={"locale": "en", "strength": 2},
        ),
        # Index 3: compound untuk query filter posture_label + sort timestamp
        IndexModel(
            [("posture_label", ASCENDING), ("timestamp", DESCENDING)],
            name="idx_posture_label_timestamp",
        ),
    ]

    created = await collection.create_indexes(indexes)
    logger.info(
        "MongoDB indexes berhasil dibuat/diverifikasi pada collection '%s': %s",
        COLLECTION_NAME,
        created,
    )


# ─── Standalone entry point ───────────────────────────────────────────────────


async def _main() -> None:
    """
    Jalankan create_indexes() sebagai standalone script.
    Membaca MONGODB_URI dan DATABASE_NAME dari environment atau file .env.
    """
    # Coba load .env jika python-dotenv tersedia
    try:
        from dotenv import load_dotenv

        # Cari .env relatif terhadap lokasi script ini
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        load_dotenv(dotenv_path=os.path.abspath(env_path))
        logger.debug("File .env dimuat dari: %s", env_path)
    except ImportError:
        pass  # python-dotenv tidak diinstall, lanjut dengan env vars OS

    mongodb_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("DATABASE_NAME")

    missing = [
        name
        for name, val in [("MONGODB_URI", mongodb_uri), ("DATABASE_NAME", database_name)]
        if not val
    ]
    if missing:
        print(
            f"ERROR: Variabel konfigurasi wajib tidak tersedia: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    client = AsyncIOMotorClient(mongodb_uri)
    try:
        db = client[database_name]
        await create_indexes(db)
        print(
            f"Indexes berhasil dibuat pada database '{database_name}', "
            f"collection '{COLLECTION_NAME}'."
        )
    finally:
        client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
