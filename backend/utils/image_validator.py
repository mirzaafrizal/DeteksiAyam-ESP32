"""
ImageValidator utility — validates uploaded image files before processing.

Checks (in order):
1. File presence            → 422 MISSING_FILE
2. File size > 0            → 422 EMPTY_FILE
3. MIME type + magic bytes  → 415 UNSUPPORTED_FORMAT
4. File size ≤ MAX_FILE_SIZE_BYTES → 413 FILE_TOO_LARGE
"""

from fastapi import HTTPException, UploadFile

from config import get_settings

# Magic byte signatures
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# Longest magic sequence is 8 bytes (PNG); read that many to cover both formats
_MAGIC_BYTES_TO_READ = 8

# Allowed MIME types
_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}


class ImageValidator:
    """Validates an UploadFile before it is passed to the inference pipeline."""

    async def validate(self, file: UploadFile | None) -> bytes:
        """
        Validate *file* and return its full content as bytes.

        The file's read position is rewound to 0 after reading so that
        downstream consumers can read the file again without issues.

        Raises:
            HTTPException(422) — file missing, or file is 0 bytes
            HTTPException(415) — format is not JPEG or PNG
            HTTPException(413) — file exceeds MAX_FILE_SIZE_BYTES
        """
        settings = get_settings()

        # ── 1. File presence ────────────────────────────────────────────────
        if file is None or not hasattr(file, "read"):
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "MISSING_FILE",
                    "message": (
                        "Tidak ada file gambar yang ditemukan dalam request. "
                        "Pastikan field 'file' dikirimkan sebagai multipart/form-data."
                    ),
                    "status_code": 422,
                },
            )

        # ── 2. Read entire content (needed for size + magic check) ──────────
        content: bytes = await file.read()

        # Rewind so downstream code can re-read the file if needed
        await file.seek(0)

        # ── 3. Empty file ────────────────────────────────────────────────────
        if len(content) == 0:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "EMPTY_FILE",
                    "message": (
                        "File gambar yang diunggah tidak boleh kosong (0 byte). "
                        "Pastikan file gambar memiliki isi yang valid."
                    ),
                    "status_code": 422,
                },
            )

        # ── 4. Format check: MIME type AND magic bytes ───────────────────────
        mime_type = (file.content_type or "").lower().split(";")[0].strip()
        magic = content[:_MAGIC_BYTES_TO_READ]

        mime_ok = mime_type in _ALLOWED_MIME_TYPES
        magic_ok = magic[:3] == _JPEG_MAGIC or magic == _PNG_MAGIC

        if not (mime_ok and magic_ok):
            raise HTTPException(
                status_code=415,
                detail={
                    "error": "UNSUPPORTED_FORMAT",
                    "message": (
                        "Format file tidak didukung. "
                        "Hanya file JPEG dan PNG yang diterima. "
                        f"Format yang terdeteksi: '{mime_type or 'tidak diketahui'}'."
                    ),
                    "status_code": 415,
                },
            )

        # ── 5. File size ─────────────────────────────────────────────────────
        file_size = len(content)
        max_size = settings.MAX_FILE_SIZE_BYTES

        if file_size > max_size:
            max_mb = max_size / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "FILE_TOO_LARGE",
                    "message": (
                        f"Ukuran file melebihi batas maksimum {max_mb:.0f} MB. "
                        f"Ukuran file yang diterima: {actual_mb:.1f} MB."
                    ),
                    "status_code": 413,
                },
            )

        return content
