import cv2
import mediapipe as mp
import math
import numpy as np
try:
    from picamera2 import Picamera2
except Exception:
    Picamera2 = None
import pyautogui
import time
import threading
from typing import List, Dict, Tuple, Optional

class MultiHandTracker:
    """
    Lightweight, in-process multi-hand tracker.
    - Prefers USB camera, falls back to Pi AI camera (Picamera2) and then default OpenCV device.
    - Runs a background thread that captures frames and runs MediaPipe Hands.
    - Provides get_tips(), get_primary(), and draw_tips(frame).
    - No socket/remote code; everything runs in the same service.
    """
    def __init__(self,
                 screen_size: Optional[Tuple[int,int]] = None,
                 max_hands: int = 8,
                 detection_conf: float = 0.45,
                 tracking_conf: float = 0.5,
                 roi_scale: float = 0.95,
                 target_fps: float = 30.0,
                 smoothing: float = 0.6,
                 usb_index: int = 0,
                 prefer_usb: bool = True):
        self.screen_w, self.screen_h = screen_size if screen_size else pyautogui.size()
        mp_hands = mp.solutions.hands
        self.hands = mp_hands.Hands(
            max_num_hands=max_hands,
            min_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf
        )

        self.colors = [
            (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0),
            (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 165, 0)
        ]
        self.roi_scale = roi_scale

        # camera selection
        self._usb_index = usb_index
        self._prefer_usb = prefer_usb
        self._picam: Optional[Picamera2] = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._use_picam = False

        # thread & state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._latest_tips: List[Dict] = []
        self._last_seen: Dict[int, float] = {}
        self._smoothed: Dict[int, Tuple[int,int]] = {}
        self._smoothed_roi: Dict[int, Tuple[int,int]] = {}
        self._alpha = smoothing
        self._target_dt = 1.0 / max(5.0, min(target_fps, 60.0))

    def start(self):
        if self._running:
            return

        # Try USB camera first
        if self._prefer_usb:
            try:
                cap = cv2.VideoCapture(self._usb_index)
                try:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_FPS, int(min(60, 1.0 / max(0.001, self._target_dt))))
                except Exception:
                    pass
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        self._cap = cap
                        self._use_picam = False
                    else:
                        try: cap.release()
                        except Exception: pass
                else:
                    try: cap.release()
                    except Exception: pass
            except Exception:
                self._cap = None

        # Fall back to Picamera2 (AI camera)
        if self._cap is None and Picamera2 is not None:
            try:
                self._picam = Picamera2()
                try:
                    cfg = self._picam.create_preview_configuration(main={"size": (800, 600)})
                except Exception:
                    cfg = self._picam.create_preview_configuration(main={"size": (640, 480)})
                self._picam.configure(cfg)
                try:
                    self._picam.set_controls({
                        "ExposureTime": 20000,
                        "AnalogueGain": 4.0,
                        "Brightness": 0.3,
                        "AwbEnable": True
                    })
                except Exception:
                    pass
                self._picam.start()
                try:
                    self._picam.set_controls({"AfMode": 1})
                except Exception:
                    pass
                self._use_picam = True
            except Exception:
                self._picam = None
                self._use_picam = False

        # Final fallback: default OpenCV device 0
        if self._cap is None and not self._use_picam:
            try:
                self._cap = cv2.VideoCapture(0)
                try:
                    self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self._cap.set(cv2.CAP_PROP_FPS, int(min(60, 1.0 / max(0.001, self._target_dt))))
                except Exception:
                    pass
            except Exception:
                self._cap = None

        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        time.sleep(0.05)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
            self._thread = None
        if self._picam:
            try:
                self._picam.stop()
            except Exception:
                pass
            self._picam = None
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        try:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            lab = cv2.merge([l, a, b])
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            gamma = 1.15
            lut = np.array([((i/255.0)**(1.0/gamma))*255 for i in np.arange(0,256)]).astype("uint8")
            frame = cv2.LUT(frame, lut)
        except Exception:
            pass
        return frame

    @staticmethod
    def _distance_coords(a, b) -> float:
        return math.hypot(a[0]-b[0], a[1]-b[1])

    def _capture_frame(self) -> Optional[np.ndarray]:
        if self._picam:
            try:
                return self._picam.capture_array()
            except Exception:
                return None
        if self._cap:
            ret, frame = self._cap.read()
            if not ret:
                try:
                    self._cap.release()
                    self._cap = cv2.VideoCapture(0)
                except Exception:
                    pass
                return None
            return frame
        return None

    def _worker(self):
        """Capture + MediaPipe processing loop."""
        while self._running:
            t0 = time.time()
            frame = self._capture_frame()
            if frame is None:
                time.sleep(self._target_dt)
                continue

            frame = self.enhance_frame(frame)
            h, w = frame.shape[:2]

            roi_w = int(w * self.roi_scale)
            roi_h = int(roi_w * 9 / 16)
            x_start = (w - roi_w) // 2
            y_start = (h - roi_h) // 2
            x_end, y_end = x_start + roi_w, y_start + roi_h

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                res = self.hands.process(rgb)
            except Exception:
                res = None

            tips = []
            if getattr(res, "multi_hand_landmarks", None):
                for idx, hand_landmarks in enumerate(res.multi_hand_landmarks):
                    tip = hand_landmarks.landmark[8]
                    pip = hand_landmarks.landmark[6]
                    extended = self._distance_coords((tip.x, tip.y, tip.z if hasattr(tip,'z') else 0),
                                                     (pip.x, pip.y, pip.z if hasattr(pip,'z') else 0)) > 0.02
                    x_tip = int(tip.x * w)
                    y_tip = int(tip.y * h)
                    if x_start <= x_tip <= x_end and y_start <= y_tip <= y_end and extended:
                        rel_x = (min(max(x_tip, x_start), x_end) - x_start) / max(1, roi_w)
                        rel_y = (min(max(y_tip, y_start), y_end) - y_start) / max(1, roi_h)
                        screen_x = int(rel_x * self.screen_w)
                        screen_y = int(rel_y * self.screen_h)
                        tips.append({"screen": (screen_x, screen_y), "roi": (x_tip, y_tip), "hand_idx": idx})

            now = time.time()
            with self._lock:
                new_smoothed: Dict[int, Tuple[int,int]] = {}
                new_smoothed_roi: Dict[int, Tuple[int,int]] = {}
                for t in tips:
                    hid = t["hand_idx"]
                    cur_screen = t["screen"]
                    cur_roi = t["roi"]
                    if hid in self._smoothed:
                        sx, sy = self._smoothed[hid]
                        rx, ry = self._smoothed_roi.get(hid, cur_roi)
                        ax = self._alpha
                        nx = int(round(ax * sx + (1 - ax) * cur_screen[0]))
                        ny = int(round(ax * sy + (1 - ax) * cur_screen[1]))
                        nrx = int(round(ax * rx + (1 - ax) * cur_roi[0]))
                        nry = int(round(ax * ry + (1 - ax) * cur_roi[1]))
                        new_smoothed[hid] = (nx, ny)
                        new_smoothed_roi[hid] = (nrx, nry)
                    else:
                        new_smoothed[hid] = (cur_screen[0], cur_screen[1])
                        new_smoothed_roi[hid] = (cur_roi[0], cur_roi[1])
                    self._last_seen[hid] = now

                for hid, (sx, sy) in list(self._smoothed.items()):
                    if hid not in new_smoothed:
                        age = now - self._last_seen.get(hid, 0)
                        if age < 0.25:
                            new_smoothed[hid] = (sx, sy)
                            if hid in self._smoothed_roi:
                                new_smoothed_roi[hid] = self._smoothed_roi[hid]
                        else:
                            self._last_seen.pop(hid, None)

                self._smoothed = new_smoothed
                self._smoothed_roi = new_smoothed_roi

                out = []
                for k in sorted(self._smoothed.keys()):
                    item = {"screen": self._smoothed[k], "hand_idx": k}
                    roi = self._smoothed_roi.get(k)
                    if roi is not None:
                        item["roi"] = roi
                    out.append(item)
                self._latest_tips = out

            elapsed = time.time() - t0
            to_sleep = max(0.0, self._target_dt - elapsed)
            time.sleep(to_sleep)

    def draw_tips(self, frame: np.ndarray) -> np.ndarray:
        if frame is None:
            return frame
        h, w = frame.shape[:2]
        with self._lock:
            for hid, roi in self._smoothed_roi.items():
                if roi is None:
                    continue
                rx, ry = int(roi[0]), int(roi[1])
                col = self.colors[hid % len(self.colors)]
                radius = max(6, int(min(w, h) * 0.025))
                try:
                    cv2.circle(frame, (rx, ry), radius, col, 2)
                    cv2.circle(frame, (rx, ry), max(2, radius // 3), col, -1)
                except Exception:
                    pass
        return frame

    def get_tips(self) -> List[Dict]:
        with self._lock:
            return list(self._latest_tips)

    def get_primary(self) -> Optional[Tuple[int,int]]:
        tips = self.get_tips()
        if not tips:
            return None
        return tips[0]["screen"]
