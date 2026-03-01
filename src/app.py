import os
import time
import logging
import cv2
import requests
from datetime import datetime
from pathlib import Path

# ── Load .env ─────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

# ── LOGGING (must be before any project imports) ──────
_log_level = logging.getLevelName(os.getenv("LOG_LEVEL", "INFO"))
logging.getLogger().handlers.clear()          # evict any handlers set by imports so far
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,                               # Python 3.8+ — overrides existing config
)
log = logging.getLogger("esp32cam")
log.info("Logging initialized at level %s", os.getenv("LOG_LEVEL", "INFO"))

# ── Project imports (after logging is configured) ─────
from notifiers.telegram.main import TelegramBot
from esp32.main import ESP32Camera

# ── CONFIG ────────────────────────────────────────────
CAMERA_IP  = os.environ["CAMERA_IP"].strip()
BOT_TOKEN = os.environ["BOT_TOKEN"].strip()
CHAT_ID   = os.environ["CHAT_ID"].strip()

STREAM_URL  = f"http://{CAMERA_IP}:81/stream"
CAPTURE_URL = f"http://{CAMERA_IP}/capture"
CONTROL_URL = f"http://{CAMERA_IP}/control"

# ── MOTION CONFIG ─────────────────────────────────────
MOTION_THRESHOLD = int(os.getenv("MOTION_THRESHOLD", "25"))
MIN_AREA         = int(os.getenv("MIN_AREA",         "1500"))
COOLDOWN         = float(os.getenv("COOLDOWN",       "5.0"))
STREAM_INTERVAL  = float(os.getenv("STREAM_INTERVAL", "3.0"))
DRAW_BOXES       = os.getenv("DRAW_BOXES", "true").lower() == "true"

GUIDELINES = (
    "📷 *ESP32-CAM Online*\n\n"
    "Commands:\n"
    "/snapshot — take photo\n"
    "/stream_on — periodic frames\n"
    "/stream_off — stop periodic\n"
    "/motion_on — enable motion alerts\n"
    "/motion_off — disable motion alerts\n"
    "/sensitivity high|medium|low\n"
    "/interval N — set stream interval (sec)\n"
    "/status — show current config\n"
    "/night_on — night mode\n"
    "/night_off — night mode off\n"
    "/flip — toggle vertical flip\n"
    "/mirror — toggle h-mirror\n"
    "/guidelines — show this help\n"
    "/led_on — turn LED on (full brightness)\n"
    "/led_off — turn LED off\n"
    "/led N — set LED brightness 0-255"
)

# ── INSTANCES ─────────────────────────────────────────
bot = TelegramBot(token=BOT_TOKEN, chat_id=CHAT_ID)

# instantiation
cam = ESP32Camera(
    stream_url=STREAM_URL,
    capture_url=CAPTURE_URL,
    control_url=CONTROL_URL,
    motion_threshold=MOTION_THRESHOLD,
    min_area=MIN_AREA,
    draw_boxes=DRAW_BOXES,
)

# ── HELPERS ───────────────────────────────────────────

def test_telegram():
    log.info("Testing Telegram connection ...")
    if bot.send_message("ESP32-CAM startup test - Telegram OK"):
        log.info("Telegram connection OK")
    else:
        log.critical("Telegram test FAILED - check BOT_TOKEN / CHAT_ID and network.")
        raise SystemExit(1)

# ── MAIN ──────────────────────────────────────────────

def main():
    global MOTION_THRESHOLD, MIN_AREA, COOLDOWN, STREAM_INTERVAL

    log.info("ESP32-CAM -> Telegram | ESP32: %s | Chat ID: %s", CAMERA_IP, CHAT_ID)

    test_telegram()
    bot.send_message(GUIDELINES)

    prev_gray     = None
    last_motion   = 0
    last_stream   = 0
    motion_on     = False
    stream_on     = False
    motion_count  = 0
    stream_count  = 0
    update_offset = 0
    vflip         = 0
    hmirror       = 0

    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}"

    while True:
        try:
            # ── Poll Telegram commands ────────────────
            resp = requests.get(
                f"{telegram_url}/getUpdates",
                params={'timeout': 1, 'offset': update_offset},
                timeout=6,
            )
            if resp.ok:
                for update in resp.json().get('result', []):
                    update_offset = update['update_id'] + 1
                    text = update.get('message', {}).get('text', '').strip().lower()
                    log.debug("Command received: %s", text)

                    if text == '/snapshot':
                        jpg = cam.get_snapshot() or cam.get_frame()
                        if jpg:
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            bot.send_photo(jpg, f"Snapshot\n{ts}")
                            log.info("Snapshot sent")
                        else:
                            bot.send_message("Could not capture frame")
                            log.warning("Snapshot capture returned nothing")

                    elif text == '/stream_on':
                        stream_on = True
                        bot.send_message(f"Stream ON - every {STREAM_INTERVAL:.0f}s")
                        log.info("Stream ON (interval=%.0fs)", STREAM_INTERVAL)

                    elif text == '/stream_off':
                        stream_on = False
                        bot.send_message("Stream OFF")
                        log.info("Stream OFF")

                    elif text == '/motion_on':
                        motion_on = True
                        prev_gray = None
                        bot.send_message("Motion detection ON")
                        log.info("Motion detection ON")

                    elif text == '/motion_off':
                        motion_on = False
                        bot.send_message("Motion detection OFF")
                        log.info("Motion detection OFF")

                    elif text.startswith('/sensitivity'):
                        parts = text.split()
                        level = parts[1] if len(parts) > 1 else 'medium'
                        presets = {
                            'high':   (10, 500,  2),
                            'medium': (25, 1500, 5),
                            'low':    (40, 3000, 10),
                        }
                        if level in presets:
                            MOTION_THRESHOLD, MIN_AREA, COOLDOWN = presets[level]
                            cam.motion_threshold = MOTION_THRESHOLD
                            cam.min_area         = MIN_AREA
                            bot.send_message(
                                f"Sensitivity: {level.upper()}\n"
                                f"Threshold: {MOTION_THRESHOLD}\n"
                                f"Min area: {MIN_AREA}\n"
                                f"Cooldown: {COOLDOWN}s"
                            )
                            log.info("Sensitivity -> %s (threshold=%d, min_area=%d, cooldown=%.0fs)",
                                     level, MOTION_THRESHOLD, MIN_AREA, COOLDOWN)
                        else:
                            log.warning("Unknown sensitivity level: %s", level)

                    elif text.startswith('/interval'):
                        parts = text.split()
                        if len(parts) > 1:
                            STREAM_INTERVAL = float(parts[1])
                            bot.send_message(f"Interval set to {STREAM_INTERVAL:.0f}s")
                            log.info("Stream interval -> %.0fs", STREAM_INTERVAL)

                    elif text == '/night_on':
                        cam.set_camera('special_effect', 2)
                        bot.send_message("Night mode ON")
                        log.info("Night mode ON")

                    elif text == '/night_off':
                        cam.set_camera('special_effect', 0)
                        bot.send_message("Night mode OFF")
                        log.info("Night mode OFF")

                    elif text == '/flip':
                        vflip = 1 - vflip
                        state = 'ON' if vflip else 'OFF'
                        cam.set_camera('vflip', vflip)
                        bot.send_message(f"V-Flip: {state}")
                        log.info("V-Flip: %s", state)

                    elif text == '/mirror':
                        hmirror = 1 - hmirror
                        state = 'ON' if hmirror else 'OFF'
                        cam.set_camera('hmirror', hmirror)
                        bot.send_message(f"H-Mirror: {state}")
                        log.info("H-Mirror: %s", state)

                    elif text == '/status':
                        bot.send_message(
                            f"Status\n"
                            f"Stream: {'ON' if stream_on else 'OFF'} ({STREAM_INTERVAL:.0f}s)\n"
                            f"Motion: {'ON' if motion_on else 'OFF'}\n"
                            f"Threshold: {MOTION_THRESHOLD}\n"
                            f"Min area: {MIN_AREA}\n"
                            f"Cooldown: {COOLDOWN}s\n"
                            f"Frames sent: {stream_count}\n"
                            f"Motion alerts: {motion_count}"
                        )
                        log.info("Status requested - frames=%d, motion_alerts=%d",
                                 stream_count, motion_count)

                    elif text == '/guidelines':
                        bot.send_message(GUIDELINES)
                        log.info("Guidelines sent")

                    elif text == "/led_on":
                        cam.set_led(255)
                        bot.send_message("LED ON (full brightness)")
                        log.info("LED ON")

                    elif text == "/led_off":
                        cam.set_led(0)
                        bot.send_message("LED OFF")
                        log.info("LED OFF")

                    elif text.startswith("/led "):
                        parts = text.split()
                        if len(parts) > 1 and parts[1].isdigit():
                            brightness = int(parts[1])
                            cam.set_led(brightness)
                            bot.send_message(f"LED brightness set to {max(0, min(255, brightness))}")
                            log.info("LED brightness -> %d", brightness)
                        else:
                            bot.send_message("Usage: /led 0-255")
                            log.warning("Invalid /led argument: %s", text)

            now = time.time()

            # ── Periodic stream ───────────────────────
            if stream_on and (now - last_stream) >= STREAM_INTERVAL:
                jpg = cam.get_snapshot() or cam.get_frame()
                if jpg:
                    ts = datetime.now().strftime("%H:%M:%S")
                    bot.send_photo(jpg, f"Stream {ts}")
                    stream_count += 1
                    last_stream = now
                    log.info("Stream frame #%d sent", stream_count)
                else:
                    log.warning("Stream: frame capture returned nothing")

            # ── Motion detection ──────────────────────
            if motion_on:
                jpg = cam.get_frame()
                if jpg:
                    frame = ESP32Camera.jpg_to_frame(jpg)
                    if frame is not None:
                        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        curr_gray = cv2.GaussianBlur(curr_gray, (21, 21), 0)

                        if prev_gray is not None:
                            motion, annotated, pct = cam.detect_motion(prev_gray, curr_gray, frame)
                            if motion and (now - last_motion) >= COOLDOWN:
                                motion_count += 1
                                ts      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                jpg_out = ESP32Camera.frame_to_jpg(annotated)
                                bot.send_photo(
                                    jpg_out,
                                    f"Motion Detected! #{motion_count}\n"
                                    f"{ts}\n"
                                    f"{pct}% of frame",
                                )
                                last_motion = now
                                log.info("Motion alert #%d - %.1f%% of frame", motion_count, pct)
                            elif motion:
                                log.debug("Motion suppressed by cooldown (%.1fs remaining)",
                                          COOLDOWN - (now - last_motion))

                        prev_gray = curr_gray

        except KeyboardInterrupt:
            log.info("Interrupted by user - shutting down.")
            bot.send_message(
                f"ESP32-CAM offline\n"
                f"Frames sent: {stream_count}\n"
                f"Motion alerts: {motion_count}"
            )
            break
        except Exception:
            log.exception("Unhandled error in main loop")
            time.sleep(2)


if __name__ == "__main__":
    main()