#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// ==========================================
// 1. PENGATURAN WIFI & IP LAPTOP (HOTSPOT KANTOR)
// ==========================================
const char* ssid = "POCOF3";
const char* password = "sayangkamu";

String ip_laptop = "10.56.64.130"; // IP terbaru Anda
String url_upload = "http://" + ip_laptop + ":8000/upload";
String url_ping   = "http://" + ip_laptop + ":8000/api/esp32/ping";

// ==========================================
// 2. PENGATURAN PIN KAMERA ESP32-CAM BISA (AI-THINKER OV2640)
// ==========================================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

unsigned long lastPingTime = 0;
const unsigned long pingInterval = 3000;

void setup() {
  Serial.begin(115200);
  delay(2000);

  WiFi.begin(ssid, password);
  Serial.print("\nMenghubungkan ke WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi Terhubung!");
  Serial.print("IP ESP32 Anda: ");
  Serial.println(WiFi.localIP());

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA; 
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("❌ Gagal Inisialisasi! Error: 0x%x\n", err);
    return;
  }
  
  // Pengaturan Sensor untuk OV2640
  sensor_t *s = esp_camera_sensor_get();
  // Jika posisi kamera terbalik saat dipasang, aktifkan 2 baris ini:
  // s->set_vflip(s, 1);   // Balik atas-bawah
  // s->set_hmirror(s, 1); // Balik kiri-kanan
  
  Serial.println("✅ Kamera Siap! Sistem Terhubung...");
  delay(2000); 
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    
    // ==========================================
    // TUGAS 1: ABSEN PING (DIKIRIM TIAP 3 DETIK)
    // ==========================================
    if (millis() - lastPingTime > pingInterval) {
      HTTPClient httpPing;
      httpPing.begin(url_ping);
      int pingCode = httpPing.GET();
      if (pingCode == 200) {
        Serial.print("🟢 Absen: OK | ");
      }
      httpPing.end();
      lastPingTime = millis();
    }

    // ==========================================
    // TUGAS 2: JEPRET FOTO (DIUBAH JADI 1 DETIK)
    // ==========================================
    static unsigned long lastCaptureTime = 0;
    
    // 1000 milidetik = 1 detik
    const unsigned long captureInterval = 1000; 

    if (millis() - lastCaptureTime > captureInterval) {
      
      camera_fb_t * fb = esp_camera_fb_get();
      if (!fb) {
        Serial.println("❌ Gagal mengambil foto!");
        return;
      }

      Serial.println("📸 Cekrek! Mengirim gambar...");

      String boundary = "----ESP32BoundaryUpload";
      String head = "--" + boundary + "\r\n";
      head += "Content-Disposition: form-data; name=\"file\"; filename=\"ayam.jpg\"\r\n";
      head += "Content-Type: image/jpeg\r\n\r\n";
      String tail = "\r\n--" + boundary + "--\r\n";

      size_t extra_len = head.length() + tail.length();
      size_t total_len = fb->len + extra_len;

      uint8_t *canvas = (uint8_t *)ps_malloc(total_len); 
      if (!canvas) {
        Serial.println("❌ PSRAM Penuh! Gambar batal dikirim.");
        esp_camera_fb_return(fb);
        return;
      }

      memcpy(canvas, head.c_str(), head.length());
      memcpy(canvas + head.length(), fb->buf, fb->len);
      memcpy(canvas + head.length() + fb->len, tail.c_str(), tail.length());

      HTTPClient http;
      http.begin(url_upload);
      http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
      
      int httpResponseCode = http.POST(canvas, total_len);
      
      free(canvas);
      esp_camera_fb_return(fb); 

      if (httpResponseCode == 200) {
        Serial.println("✅ Foto terkirim!");
      } else {
        Serial.printf("❌ Gagal kirim (HTTP Code: %d)\n", httpResponseCode);
      }
      
      http.end();
      
      // Reset waktu jepret
      lastCaptureTime = millis(); 
    }
  }
}