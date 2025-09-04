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
from typing import List, Dict, Tuple, Optional

class MultiHandTracker:
    """
    Multi-hand tracker usable from main loop.
    Methods:
      start() -> start camera resources
      stop()  -> stop camera resources
      get_tips() -> List[{"screen":(x,y),"roi":(x_tip,y_tip),"hand_idx":i}]
      get_primary() -> (x,y) or None
    """
    def __init__(self, screen_size: Tuple[int,int]=None, max_hands: int = 8,
                 detection_conf: float = 0.6, tracking_conf: float = 0.5,
                 roi_scale: float = 0.8):
        self.screen_w, self.screen_h = screen_size if screen_size else pyautogui.size()
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_hands,
            min_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf
        )
        self.colors = [
            (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0),
            (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 165, 0)
        ]
        self.roi_scale = roi_scale

        self._use_picam = Picamera2 is not None
        self._picam = None
        self._cap = None
        self._running = False

    def start(self):
        if self._running:
            return
        if self._use_picam:
            try:
                self._picam = Picamera2()
                config = self._picam.create_preview_configuration(main={"size": (800, 600)})
                self._picam.configure(config)
                # gentle low-light defaults (adjust on-device if necessary)
                try:
                    self._picam.set_controls({
                        "ExposureTime": 25000,
                        "AnalogueGain": 4.0,
                        "Brightness": 0.3
                    })
                except Exception:
                    pass
                self._picam.start()
            except Exception:
                self._picam = None
                self._use_picam = False
        if not self._use_picam:
            # fallback to webcam
            self._cap = cv2.VideoCapture(0)
        self._running = True
        time.sleep(0.1)

    def stop(self):
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
        self._running = False

    def enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        # CLAHE on L channel + mild gamma boost for low-light robustness
        try:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            lab = cv2.merge([l, a, b])
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            gamma = 1.3
            lookUpTable = np.array([((i/255.0)**(1.0/gamma))*255 for i in np.arange(0,256)]).astype("uint8")
            frame = cv2.LUT(frame, lookUpTable)
        except Exception:
            pass
        return frame

    @staticmethod
    def _distance(a, b):
        return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)

    def _capture_frame(self) -> Optional[np.ndarray]:
        if self._picam:
            try:
                return self._picam.capture_array()
            except Exception:
                return None
        if self._cap:
            ret, frame = self._cap.read()
            if not ret:
                # try re-open
                try:
                    self._cap.release()
                    self._cap = cv2.VideoCapture(0)
                except Exception:
                    pass
                return None
            return frame
        return None

    def get_tips(self) -> List[Dict]:
        """
        Return list of detected index-finger tips mapped to screen coordinates.
        Each entry: {"screen": (x,y), "roi": (x_tip,y_tip), "hand_idx": idx}
        """
        if not self._running:
            return []

        frame = self._capture_frame()
        if frame is None:
            return []
        frame = self.enhance_frame(frame)
        h, w = frame.shape[:2]

        # compute ROI (centered)
        roi_w = int(w * self.roi_scale)
        roi_h = int(roi_w * 9 / 16)
        x_start = (w - roi_w) // 2
        y_start = (h - roi_h) // 2
        x_end, y_end = x_start + roi_w, y_start + roi_h

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        try:
            res = self.hands.process(rgb)
        except Exception:
            return []

        tips = []
        if getattr(res, "multi_hand_landmarks", None):
            for idx, hand_landmarks in enumerate(res.multi_hand_landmarks):
                tip = hand_landmarks.landmark[8]
                pip = hand_landmarks.landmark[6]
                mcp = hand_landmarks.landmark[5]
                extended = self._distance(tip, pip) > self._distance(pip, mcp) * 0.8
                x_tip = int(tip.x * w)
                y_tip = int(tip.y * h)
                if x_start <= x_tip <= x_end and y_start <= y_tip <= y_end and extended:
                    rel_x = (min(max(x_tip, x_start), x_end) - x_start) / max(1, roi_w)
                    rel_y = (min(max(y_tip, y_start), y_end) - y_start) / max(1, roi_h)
                    screen_x = int(rel_x * self.screen_w)
                    screen_y = int(rel_y * self.screen_h)
                    tips.append({"screen": (screen_x, screen_y), "roi": (x_tip, y_tip), "hand_idx": idx})
        return tips

    def get_primary(self) -> Optional[Tuple[int,int]]:
        """Return screen coords of the first detected hand tip, or None"""
        tips = self.get_tips()
        if not tips:
            return None
        return tips[0]["screen"]


# -----------------------
# Main loop
# -----------------------
tracker = MultiHandTracker(max_hands=16, detection_conf=0.7, tracking_conf=0.6, roi_scale=0.8)
tracker.start()
try:
    while True:
        tips = tracker.get_tips()
        primary = tracker.get_primary()

        # For visualization: draw tips and primary hand
        frame = tracker._capture_frame()
        if frame is not None:
            for tip in tips:
                cv2.circle(frame, tip["roi"], 10, (0,255,0), -1)
            if primary:
                cv2.circle(frame, primary, 15, (255,0,0), 3)
            cv2.imshow("Hand Tracking", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break
finally:
    tracker.stop()
    cv2.destroyAllWindows()
