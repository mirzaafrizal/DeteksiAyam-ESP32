import json
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Wajib — startup gagal jika salah satu tidak ada
    MONGODB_URI: str = ""
    DATABASE_NAME: str = ""

    # Opsional — ada default value
    MODEL_PATH: str = "models/best.pt"
    IMAGES_DIR: str = "images"
    MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5MB

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_required_vars(self) -> "Settings":
        missing = []

        if not self.MONGODB_URI:
            missing.append("MONGODB_URI")
        if not self.DATABASE_NAME:
            missing.append("DATABASE_NAME")

        if missing:
            error_payload = json.dumps(
                {
                    "error": "MISSING_CONFIG",
                    "message": (
                        "Variabel konfigurasi wajib tidak tersedia: "
                        + ", ".join(missing)
                    ),
                    "missing_variables": missing,
                }
            )
            raise ValueError(error_payload)

        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
