# DeteksiAyam-ESP32
Source code sistem deteksi postur ayam berbasis Microservices menggunakan ESP32-CAM, YOLOv8, dan FastAPI (Tugas Akhir S1 Teknik Elektro).
# 🐓 Sistem Deteksi Postur Ayam Berbasis Edge Computing & Microservices

Repositori ini memuat seluruh *source code* (kode sumber) untuk penelitian Tugas Akhir / Skripsi yang berfokus pada deteksi dini postur telungkup (abnormal) pada ayam ternak sebagai indikator awal penyakit mematikan.

Sistem ini dirancang menggunakan arsitektur **Microservices** untuk memastikan skalabilitas, efisiensi penyimpanan *database*, dan respons yang cepat.

## 🛠️ Teknologi yang Digunakan
Sistem ini terbagi menjadi 4 layanan utama:
1. **Edge Device (Hardware):** ESP32-CAM (C++/Arduino) untuk pengambilan *frame* secara *real-time*.
2. **Backend & AI Inference:** Python, FastAPI, dan model YOLOv8 (Computer Vision) untuk deteksi objek.
3. **Message Broker & Database:** RabbitMQ untuk distribusi antrean data dan MongoDB untuk penyimpanan.
4. **Frontend Dashboard:** React.js dan Node.js untuk antarmuka pemantauan *real-time*.

## 📌 Fitur Unggulan
- **Jitter Compensation & Rate Limiting:** Algoritma pembatasan pengiriman *frame* (interval 14-15 detik) untuk mencegah lonjakan data, menghemat *storage database* hingga 93,3%.
- **Arsitektur Terdistribusi:** Pemisahan beban kerja antara pengiriman gambar, inferensi AI, dan penyimpanan data, sehingga *server* tidak mengalami *bottleneck*.

---
*Dibuat untuk memenuhi persyaratan kelulusan S1 Program Studi Teknik Elektro.*
