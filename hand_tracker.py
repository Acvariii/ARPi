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
import socket
import json
from typing import List, Dict, Tuple, Optional

class MultiHandTracker:
    """
    Multi-hand tracker usable from main loop.
    Runs a background detection thread to keep get_tips() cheap and responsive.
    Smoothing applied per-hand (EMA) and stale hands removed automatically.
    Methods:
    start() -> start camera & thread
    stop()  -> stop camera & thread
    get_tips() -> List[{"screen":(x,y),"roi":(x_tip,y_tip),"hand_idx":i}]
    get_primary() -> (x,y) or None
    """
    def __init__(self, screen_size: Tuple[int,int]=None, max_hands: int = 8,
                detection_conf: float = 0.45, tracking_conf: float = 0.5,
                roi_scale: float = 0.95, target_fps: float = 45.0, smoothing: float = 0.6,
                socket_path: Optional[str]=None):
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

        # background thread
        self._running = False
        self._thread = None
        self._lock = threading.RLock()
        self._latest_tips: List[Dict] = []
        self._last_seen = {}  # hand_idx -> timestamp
        self._smoothed = {}   # hand_idx -> (x,y)
        self._alpha = smoothing  # EMA smoothing (0..1, higher = less smoothing)
        self._target_dt = 1.0 / max(5.0, min(target_fps, 60.0))

        # remote mode: if socket_path provided, operate as a client reading tip updates
        self.socket_path = socket_path
        self._remote_thread = None
        self._remote_running = False

    def start(self):
        if self._running:
            return
        # If socket_path specified, start remote client thread and do not start local capture
        if self.socket_path:
            try:
                self._remote_running = True
                self._remote_thread = threading.Thread(target=self._remote_worker, daemon=True)
                self._remote_thread.start()
                self._running = True
                return
            except Exception:
                self._remote_running = False
                self._remote_thread = None
                # fall through to local capture if remote fails
        if self._use_picam:
            try:
                self._picam = Picamera2()
                # use a modest, fast configuration; smaller frame -> faster Mediapipe inference
                try:
                    config = self._picam.create_preview_configuration(main={"size": (800, 600)})
                except Exception:
                    config = self._picam.create_preview_configuration(main={"size": (640, 480)})
                self._picam.configure(config)
                try:
                    self._picam.set_controls({
                        # best-effort autofocus / auto-exposure controls (may be ignored on some sensors)
                        "ExposureTime": 20000,
                        "AnalogueGain": 4.0,
                        "Brightness": 0.3,
                        "AwbEnable": True
                    })
                except Exception:
                    pass
                self._picam.start()
                # try a best-effort focus command if supported (not all cameras/PiISP support this)
                try:
                    # these keys may not be present; ignore failures
                    self._picam.set_controls({"AfMode": 1})
                except Exception:
                    pass
            except Exception:
                self._picam = None
                self._use_picam = False
        if not self._use_picam:
            self._cap = cv2.VideoCapture(0)
            # try to set a modest resolution for speed
            try:
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self._cap.set(cv2.CAP_PROP_FPS, int( min(60, 1.0 / max(0.001, self._target_dt)) ))
            except Exception:
                pass

        self._running = True
        # start background thread
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        # small settle
        time.sleep(0.05)

    def _remote_worker(self):
        """Connect to unix socket and read newline-delimited JSON tip messages from camera service."""
        path = self.socket_path
        while self._remote_running:
            try:
                client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client.connect(path)
                client_file = client.makefile("r")
                while self._remote_running:
                    line = client_file.readline()
                    if not line:
                        break
                    try:
                        msg = json.loads(line.strip())
                        tips = msg.get("tips", [])
                        with self._lock:
                            # convert into same smoothed structure quickly (no smoothing here)
                            now = time.time()
                            new_smoothed = {}
                            for t in tips:
                                hid = t.get("hand_idx", 0)
                                pos = tuple(t.get("screen", (0,0)))
                                new_smoothed[hid] = pos
                                self._last_seen[hid] = now
                            # keep recent old ones for short time
                            for hid, (sx, sy) in list(self._smoothed.items()):
                                if hid not in new_smoothed:
                                    age = now - self._last_seen.get(hid, 0)
                                    if age < 0.25:
                                        new_smoothed[hid] = (sx, sy)
                                    else:
                                        self._last_seen.pop(hid, None)
                            self._smoothed = new_smoothed
                            self._latest_tips = [{"screen": self._smoothed[k], "hand_idx": k} for k in sorted(self._smoothed.keys())]
                    except Exception:
                        continue
                try:
                    client.close()
                except Exception:
                    pass
            except Exception:
                time.sleep(0.25)

    def stop(self):
        # stop remote if running
        self._remote_running = False
        if self._remote_thread:
            self._remote_thread.join(timeout=0.5)
            self._remote_thread = None
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
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
        # lightweight enhancement for low-light robustness (cheap ops)
        try:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            lab = cv2.merge([l, a, b])
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            gamma = 1.15
            lookUpTable = np.array([((i/255.0)**(1.0/gamma))*255 for i in np.arange(0,256)]).astype("uint8")
            frame = cv2.LUT(frame, lookUpTable)
        except Exception:
            pass
        return frame

    @staticmethod
    def _distance_coords(a, b):
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
        """Background capture + mediapipe processing loop (keeps self._latest_tips updated)."""
        while self._running:
            t_loop = time.time()
            frame = self._capture_frame()
            if frame is None:
                time.sleep(self._target_dt)
                continue
            # lightweight enhancement only (keep cheap to preserve fps)
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
                res = None

            tips = []
            if getattr(res, "multi_hand_landmarks", None):
                for idx, hand_landmarks in enumerate(res.multi_hand_landmarks):
                    tip = hand_landmarks.landmark[8]
                    pip = hand_landmarks.landmark[6]
                    mcp = hand_landmarks.landmark[5]
                    # simple finger-extended test
                    # more permissive threshold so fingertips are detected when smaller in frame
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

            # smoothing + stale pruning
            now = time.time()
            with self._lock:
                new_smoothed = {}
                for t in tips:
                    hid = t["hand_idx"]
                    cur = t["screen"]
                    if hid in self._smoothed:
                        sx, sy = self._smoothed[hid]
                        ax = self._alpha
                        nx = int(round(ax * sx + (1 - ax) * cur[0]))
                        ny = int(round(ax * sy + (1 - ax) * cur[1]))
                        new_smoothed[hid] = (nx, ny)
                    else:
                        new_smoothed[hid] = (cur[0], cur[1])
                    self._last_seen[hid] = now

                # keep previous smoothed ones for short time if not detected (helps avoid flicker)
                for hid, (sx, sy) in list(self._smoothed.items()):
                    if hid not in new_smoothed:
                        age = now - self._last_seen.get(hid, 0)
                        if age < 0.25:  # keep for 250ms
                            new_smoothed[hid] = (sx, sy)
                        else:
                            self._last_seen.pop(hid, None)

                self._smoothed = new_smoothed
                # write latest tips list in stable order
                self._latest_tips = [{"screen": self._smoothed[k], "hand_idx": k} for k in sorted(self._smoothed.keys())]

            # sleep to target rate
            elapsed = time.time() - t_loop
            to_sleep = max(0.0, self._target_dt - elapsed)
            time.sleep(to_sleep)

    def get_tips(self) -> List[Dict]:
        """Return latest smoothed tips (cheap, thread-safe)."""
        with self._lock:
            return list(self._latest_tips)

    def get_primary(self) -> Optional[Tuple[int,int]]:
        """Return screen coords of the first detected (smoothed) hand tip, or None"""
        tips = self.get_tips()
        if not tips:
            return None
        return tips[0]["screen"]
