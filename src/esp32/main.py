import requests
import logging
import cv2
import numpy as np
from datetime import datetime

class ESP32Camera:
    def __init__(self, stream_url: str, capture_url: str, control_url: str,
                 motion_threshold: int = 25, min_area: int = 500,
                 draw_boxes: bool = True):
        self.stream_url        = stream_url
        self.capture_url       = capture_url
        self.control_url      = control_url
        self.motion_threshold  = motion_threshold
        self.min_area          = min_area
        self.draw_boxes        = draw_boxes
        self.log               = logging.getLogger(self.__class__.__name__)

    # ── Camera control ────────────────────────────────

    def set_led(self, intensity: int) -> None:
        self.brightness = max(0, min(255, intensity))
        try:
            resp = requests.get(
                f"{self.control_url}?var=led_intensity&val={self.brightness}", timeout=3)
            if not resp.ok:
                self.log.warning("set_led HTTP %s", resp.status_code)
            self.log.debug("LED intensity = %d", self.brightness)
        except Exception:
            self.log.warning("set_led failed (intensity=%d)", self.brightness)

    def set_camera(self, key: str, val) -> None:
        try:
            requests.get(f"{self.control_url}?var={key}&val={val}", timeout=3)
            self.log.debug("camera %s = %s", key, val)
        except Exception:
            self.log.warning("set_camera failed for %s=%s", key, val)

    def toggle_vflip(self) -> str:
        self.vflip = 1 - self.vflip
        self.set_camera('vflip', self.vflip)
        return 'ON' if self.vflip else 'OFF'

    def toggle_hmirror(self) -> str:
        self.hmirror = 1 - self.hmirror
        self.set_camera('hmirror', self.hmirror)
        return 'ON' if self.hmirror else 'OFF'

    # ── Capture ───────────────────────────────────────────────────────────────

    def get_frame(self) -> bytes | None:
        """Grab one JPEG frame from ESP32 stream."""
        try:
            stream = requests.get(self.stream_url, stream=True, timeout=10)
            buffer = bytes()
            for chunk in stream.iter_content(chunk_size=4096):
                buffer += chunk
                start = buffer.find(b'\xff\xd8')
                end   = buffer.find(b'\xff\xd9')
                if start != -1 and end != -1:
                    jpg = buffer[start:end + 2]
                    stream.close()
                    return jpg
        except Exception:
            self.log.exception("get_frame failed")
        return None

    def get_snapshot(self) -> bytes | None:
        """Get single capture from /capture endpoint (faster)."""
        try:
            resp = requests.get(self.capture_url, timeout=5)
            if resp.ok:
                return resp.content
        except Exception:
            self.log.exception("get_snapshot failed")
        return None

    # ── Conversion ────────────────────────────────────────────────────────────

    @staticmethod
    def jpg_to_frame(jpg_bytes: bytes):
        arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    @staticmethod
    def frame_to_jpg(frame, quality: int = 85) -> bytes:
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes()

    # ── Motion detection ──────────────────────────────────────────────────────

    def detect_motion(self, prev_gray, curr_gray, frame) -> tuple[bool, any, float]:
        diff        = cv2.absdiff(prev_gray, curr_gray)
        blur        = cv2.GaussianBlur(diff, (5, 5), 0)
        _, thresh   = cv2.threshold(blur, self.motion_threshold, 255, cv2.THRESH_BINARY)
        dilated     = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = False
        annotated       = frame.copy()

        for c in contours:
            if cv2.contourArea(c) < self.min_area:
                continue
            motion_detected = True
            if self.draw_boxes:
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(annotated, "MOTION", (x, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated, ts, (10, annotated.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        motion_pixels = cv2.countNonZero(thresh)
        total_pixels  = thresh.shape[0] * thresh.shape[1]
        motion_pct    = round((motion_pixels / total_pixels) * 100, 1)

        return motion_detected, annotated, motion_pct