from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
from typing import Optional

# Enum ini tetap dibiarkan saja sebagai referensi (tidak dihapus)
class PostureLabel(str, Enum):
    NORMAL = "Normal"
    DUDUK_TIDAK_TEGAK = "Duduk Tidak Tegak"
    TELUNGKUP = "Telungkup"


class DetectionLogCreate(BaseModel):
    timestamp: datetime
    # ── UBAH JADI str: Supaya bebas nerima kata "Tidak Ada Ayam" ──
    posture_label: str  
    confidence_score: float = Field(ge=0.0, le=1.0)
    image_url: str = Field(max_length=2048)
    
    # 👇 TAMBAHAN FIELD JUMLAH AYAM 👇
    jumlah_ayam: int = 0
    
    # ── TAMBAHAN FIELD LATENSI: Biar data skripsinya masuk ke DB ──
    waktu_terima_esp: Optional[str] = ""
    waktu_mulai_yolo: Optional[str] = ""
    durasi_total_detik: Optional[float] = 0.0

    @field_validator("posture_label")
    @classmethod
    def validate_posture_label_length(cls, v: str) -> str:
        # Karena v sekarang string, hapus ".value" biar tidak error
        if len(v) > 50:
            raise ValueError("posture_label melebihi 50 karakter")
        return v


class DetectionLogResponse(BaseModel):
    id: str = Field(alias="_id")
    timestamp: datetime
    # ── UBAH JADI str: Sama seperti di atas ──
    posture_label: str  
    confidence_score: float
    image_url: str
    
    # 👇 TAMBAHAN FIELD JUMLAH AYAM 👇
    jumlah_ayam: int = 0
    
    # Tambahkan ke response agar bisa dibaca jika butuh ditarik ke Frontend
    waktu_terima_esp: Optional[str] = ""
    waktu_mulai_yolo: Optional[str] = ""
    durasi_total_detik: Optional[float] = 0.0

    model_config = {"populate_by_name": True}