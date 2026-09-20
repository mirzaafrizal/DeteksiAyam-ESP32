# Backend Setup Guide

## Prerequisites

- Python 3.10 atau lebih baru
- MongoDB Atlas account (atau MongoDB lokal)

---

## 1. Buat Virtual Environment

Dari folder `backend/`:

```bash
python -m venv venv
```

## 2. Aktivasi Virtual Environment

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

Setelah aktivasi, prompt terminal akan berubah menjadi `(venv) ...`.

## 3. Install Dependensi

```bash
pip install -r requirements.txt
```

## 4. Konfigurasi Environment Variables

Salin file contoh dan isi dengan kredensial MongoDB Atlas:

```bash
cp .env.example .env
```

Edit `.env` dan ganti nilai placeholder dengan kredensial asli.

## 5. Jalankan Server

```bash
uvicorn main:app --reload
```

Server berjalan di `http://localhost:8000`.  
Swagger UI tersedia di `http://localhost:8000/docs`.

## 6. Jalankan Tests

```bash
pytest
```

---

## Dependensi

| Package | Versi | Kegunaan |
|---|---|---|
| `fastapi` | 0.111.0 | Web framework async |
| `uvicorn[standard]` | 0.29.0 | ASGI server |
| `motor` | 3.4.0 | Driver MongoDB async |
| `pydantic-settings` | 2.2.1 | Manajemen konfigurasi env vars |
| `python-multipart` | 0.0.9 | Parsing multipart form data (upload file) |
| `Pillow` | 10.3.0 | Pemrosesan dan validasi gambar |
| `python-dotenv` | 1.0.1 | Loading file `.env` |
| `pytest` | 8.2.0 | Framework testing |
| `pytest-asyncio` | 0.23.6 | Dukungan async untuk pytest |
| `httpx` | 0.27.0 | HTTP client untuk integration tests |
| `hypothesis` | 6.100.0 | Library property-based testing |
