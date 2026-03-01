#include "esp_camera.h"
#include "secrets.h"
#include <WiFi.h>

#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

const char* ssid     = SECRET_SSID;
const char* password = SECRET_PASSWORD;

void startCameraServer();
void setupLedFlash();

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  camera_config_t config;
  config.ledc_channel  = LEDC_CHANNEL_0;
  config.ledc_timer    = LEDC_TIMER_0;
  config.pin_d0        = Y2_GPIO_NUM;
  config.pin_d1        = Y3_GPIO_NUM;
  config.pin_d2        = Y4_GPIO_NUM;
  config.pin_d3        = Y5_GPIO_NUM;
  config.pin_d4        = Y6_GPIO_NUM;
  config.pin_d5        = Y7_GPIO_NUM;
  config.pin_d6        = Y8_GPIO_NUM;
  config.pin_d7        = Y9_GPIO_NUM;
  config.pin_xclk      = XCLK_GPIO_NUM;
  config.pin_pclk      = PCLK_GPIO_NUM;
  config.pin_vsync     = VSYNC_GPIO_NUM;
  config.pin_href      = HREF_GPIO_NUM;
  config.pin_sscb_sda  = SIOD_GPIO_NUM;
  config.pin_sscb_scl  = SIOC_GPIO_NUM;
  config.pin_pwdn      = PWDN_GPIO_NUM;
  config.pin_reset     = RESET_GPIO_NUM;
  config.xclk_freq_hz  = 20000000;
  config.pixel_format  = PIXFORMAT_JPEG;
  config.frame_size    = FRAMESIZE_QVGA;
  config.jpeg_quality  = 10;
  config.fb_count      = 2;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return;
  }
  Serial.println("Camera OK");

  // ── Network config from secrets.h ─────────────────
  IPAddress local_IP, gateway, subnet;
  local_IP.fromString(CAMERA_IP);
  gateway.fromString(CAMERA_GATEWAY);
  subnet.fromString(CAMERA_SUBNET);
  WiFi.config(local_IP, gateway, subnet);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println("\nWiFi Connected!");
  Serial.printf("Camera Stream:  http://%s:81/stream\n", WiFi.localIP().toString().c_str());
  Serial.printf("Camera Control: http://%s\n", WiFi.localIP().toString().c_str());

  startCameraServer();
}

void loop() {}
