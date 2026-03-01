from pathlib import Path
from dotenv import dotenv_values

ROOT     = Path(__file__).resolve().parents[4]  # src/core/arduino/init → root
ENV_FILE = ROOT / ".env"
OUT_FILE = ROOT / "src" / "core" / "arduino" / "CameraWebServer" / "secrets.h"

config = dotenv_values(ENV_FILE)

print(f"Loading .env from: {ENV_FILE}")
print(f"Keys found: {list(config.keys())}")

template = """\
// Auto-generated from .env — do not edit or commit
#pragma once

#define SECRET_SSID        "{WIFI_SSID}"
#define SECRET_PASSWORD    "{WIFI_PASSWORD}"
#define CAMERA_IP          "{CAMERA_IP}"
#define CAMERA_GATEWAY     "{CAMERA_GATEWAY}"
#define CAMERA_SUBNET      "{CAMERA_SUBNET}"
""".format(**config)

OUT_FILE.write_text(template)
print(f"secrets.h written to {OUT_FILE}")