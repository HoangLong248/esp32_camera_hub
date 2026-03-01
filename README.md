# ESP32 Camera Hub

A multi-platform camera monitoring system built on the **ESP32-CAM**. Stream live video, capture snapshots, and forward alerts to **Slack**, **Telegram**, **Discord**, or any **Webhook**-compatible service.

---

## 📁 Project Structure

```
├── .env                        # Secrets (never commit)
├── .env.example                # Template for .env
├── .gitignore
├── README.md
├── requirements.txt
└── src
    ├── app.py                  # Main entry point
    ├── core
    │   └── arduino
    │       ├── CameraWebServer/
    │       │   ├── CameraWebServer.ino
    │       │   ├── secrets.h   # Auto-generated (never commit)
    │       │   └── ...
    │       └── init/
    │           └── generate_secrets.py
    ├── esp32/
    │   └── main.py             # ESP32 stream/capture logic
    ├── slack/
    │   └── main.py             # Slack integration
    ├── telegram/
    │   └── main.py             # Telegram integration
    ├── discord/
    │   └── main.py             # Discord integration
    └── webhook/
        └── main.py             # Generic webhook integration
```

---

## ⚙️ Requirements

- Python 3.10+
- Arduino IDE 2.x or Arduino CLI
- ESP32-CAM (AI Thinker model)
- FTDI programmer or USB-TTL adapter for flashing

---

## 🚀 Setup Guide

### 1. Clone the repository

```bash
git clone https://github.com/your-username/esp32-camera-hub.git
cd esp32-camera-hub
```

### 2. Create your `.env` file

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` and fill in the platforms you want to use:

```env
# ── ESP32 ─────────────────────────────────────────────
WIFI_SSID=your_wifi_name
WIFI_PASSWORD=your_wifi_password
CAMERA_IP=192.168.1.60
CAMERA_GATEWAY=192.168.1.1
CAMERA_SUBNET=255.255.255.0

# ── Slack ─────────────────────────────────────────────
SLACK_TOKEN=xoxb-your-slack-token
SLACK_CHANNEL=C0XXXXXXXXX

# ── Telegram ──────────────────────────────────────────
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# ── Discord ───────────────────────────────────────────
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# ── Generic Webhook ───────────────────────────────────
WEBHOOK_URL=https://your-endpoint.com/notify
```

> You only need to fill in the platforms you plan to use. Leave others blank.

> **Never commit `.env` or `secrets.h` — they are gitignored.**

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Generate `secrets.h` for Arduino

This reads your `.env` and writes `secrets.h` into the Arduino sketch folder:

```bash
python src/core/arduino/init/generate_secrets.py
```

Expected output:
```
Loading .env from: /path/to/project/.env
Keys found: ['WIFI_SSID', 'WIFI_PASSWORD', 'CAMERA_IP', ...]
secrets.h written to src/core/arduino/CameraWebServer/secrets.h
```

### 5. Flash the ESP32

1. Open `src/core/arduino/CameraWebServer/CameraWebServer.ino` in Arduino IDE
2. Install the **ESP32 board package** if not already installed:
   - Go to `File → Preferences → Additional Board Manager URLs` and add:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Then `Tools → Board → Board Manager` → search **esp32** → install
3. Select board: `Tools → Board → ESP32 Arduino → AI Thinker ESP32-CAM`
4. Select the correct port under `Tools → Port`
5. Click **Upload**

After flashing, open Serial Monitor at `115200` baud. You should see:

```
Camera OK
WiFi Connected!
Camera Stream:  http://192.168.1.60:81/stream
Camera Control: http://192.168.1.60
```

### 6. Run the Python app

```bash
python src/app.py
```

---

## 🔗 Camera Endpoints

| Endpoint | Description |
|---|---|
| `http://<CAMERA_IP>:81/stream` | MJPEG live stream |
| `http://<CAMERA_IP>/capture` | Single JPEG snapshot |
| `http://<CAMERA_IP>/control` | Camera settings control |

---

## 📡 Platform Setup

### Slack
1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Enable **Bot Token Scopes**: `chat:write`, `files:write`
3. Install the app to your workspace and copy the **Bot Token** (`xoxb-...`)
4. Copy your target **Channel ID** (right-click channel → View channel details)
5. Add both to `.env` as `SLACK_TOKEN` and `SLACK_CHANNEL`

### Telegram
1. Message [@BotFather](https://t.me/BotFather) and create a bot with `/newbot`
2. Copy the bot token into `TELEGRAM_TOKEN`
3. Get your chat ID via [@userinfobot](https://t.me/userinfobot)
4. Add it to `.env` as `TELEGRAM_CHAT_ID`

### Discord
1. Go to your Discord server → **Server Settings → Integrations → Webhooks**
2. Create a new webhook and copy the URL
3. Add it to `.env` as `DISCORD_WEBHOOK_URL`

### Generic Webhook
Any HTTP endpoint that accepts a `POST` request with a JSON body or multipart image upload. Set `WEBHOOK_URL` in `.env` to your endpoint.

---

## 🛠️ Troubleshooting

**Camera init failed**
- Check that the board selected is `AI Thinker ESP32-CAM`
- Ensure GPIO0 is pulled to GND during flashing, then disconnected for normal boot

**WiFi not connecting**
- Verify `WIFI_SSID` and `WIFI_PASSWORD` in `.env` are correct
- Make sure the router is 2.4GHz (ESP32 does not support 5GHz)
- Check that the static IP (`CAMERA_IP`) is not already taken on your network

**`secrets.h` not found**
- Run `generate_secrets.py` before flashing (Step 4 above)

**Notifications not sending**
- Double-check the relevant token/URL in `.env`
- Make sure the Python app is running (`python src/app.py`)
- For Slack: confirm the bot has been invited to the channel (`/invite @your-bot`)
