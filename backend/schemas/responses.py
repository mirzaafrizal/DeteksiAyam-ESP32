from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    message: str
    status_code: int


class UploadResponse(BaseModel):
    status: str = "success"
    posture_label: str
    confidence_score: float
    image_url: str
    log_id: str
    
    # 👇 TAMBAHAN FIELD JUMLAH AYAM 👇
    jumlah_ayam: int = 0