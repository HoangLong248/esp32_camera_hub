import requests, logging
import os
import io

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.log = logging.getLogger(self.__class__.__name__)

    def send_photo(self, jpg_bytes: bytes, caption: str = "") -> bool:
        try:
            files = {'photo': ('frame.jpg', io.BytesIO(jpg_bytes), 'image/jpeg')}
            data  = {'chat_id': self.chat_id, 'caption': caption}
            resp  = requests.post(f"{self.base_url}/sendPhoto",
                                  files=files, data=data, timeout=10)
            if not resp.ok:
                self.log.warning("send_photo HTTP %s: %s", resp.status_code, resp.text)
            return resp.ok
        except Exception:
            self.log.exception("send_photo failed")
            return False

    def send_message(self, text: str) -> bool:
        """Send a Telegram message. Returns True on success, False on failure."""
        try:
            resp = requests.post(
                f"{self.base_url}/sendMessage",
                data={'chat_id': self.chat_id, 'text': text},
                timeout=5,
            )
            if not resp.ok:
                self.log.warning("send_message HTTP %s: %s", resp.status_code, resp.text)
            return resp.ok
        except Exception:
            self.log.exception("send_message failed")
            return False