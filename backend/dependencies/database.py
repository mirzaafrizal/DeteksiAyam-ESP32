from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Request

_client: AsyncIOMotorClient = None


async def connect_db(settings) -> None:
    """Buat koneksi Motor ke MongoDB menggunakan settings yang diberikan."""
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URI)


async def close_db() -> None:
    """Tutup koneksi Motor ke MongoDB."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db(request: Request):
    """FastAPI dependency — mengembalikan database instance dari app state."""
    return _client[request.app.state.database_name]
