# ...new file...
import os
import time
import json
import socket
import math
import cv2
import mediapipe as mp
import numpy as np
try:
    from picamera2 import Picamera2
except Exception:
    Picamera2 = None

SOCKET_PATH = "/tmp/hand_tracker.sock"
TARGET_FPS = 60.0
ROI_SCALE = 0.95
DETECTION_CONF = 0.45
TRACKING_CONF = 0.5

def main(socket_path=SOCKET_PATH, target_fps=TARGET_FPS):
    # remove existing socket
    try:
        if os.path.exists(socket_path):
            os.unlink(socket_path)
    except Exception:
        pass

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=8, min_detection_confidence=DETECTION_CONF, min_tracking_confidence=TRACKING_CONF)

    # camera init: try USB OpenCV (usb index 1) first, then explicit device 0, then Picamera2 last
    picam = None
    cap = None
    tried_indices = [1, 0]  # first try a likely USB index (1), then device 0
    for idx in tried_indices:
        try:
            cap_try = cv2.VideoCapture(idx)
            try:
                cap_try.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap_try.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap_try.set(cv2.CAP_PROP_FPS, int(target_fps))
            except Exception:
                pass
            ret, _ = cap_try.read()
            if ret:
                cap = cap_try
                print(f"camera_service: using OpenCV device {idx}")
                break
            else:
                try:
                    cap_try.release()
                except Exception:
                    pass
        except Exception:
            pass

    # If no OpenCV USB device opened, try Picamera2 as a last fallback
    if cap is None and Picamera2 is not None:
        try:
            picam = Picamera2()
            try:
                cfg = picam.create_preview_configuration(main={"size": (800, 600)})
            except Exception:
                cfg = picam.create_preview_configuration(main={"size": (640, 480)})
            picam.configure(cfg)
            try:
                picam.set_controls({"ExposureTime": 20000, "AnalogueGain": 4.0, "AwbEnable": True})
            except Exception:
                pass
            picam.start()
            print("camera_service: using Picamera2 (fallback)")
        except Exception:
            picam = None
    # only use explicit device 0 if we still have no capture device and no Picamera
    if cap is None and picam is None:
        try:
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, int(target_fps))
            # quick read checks (some USB cameras need a few frames)
            ok = False
            for _ in range(3):
                ret, _ = cap.read()
                if ret:
                    ok = True
                    break
                time.sleep(0.06)
            if ok:
                print("camera_service: using fallback OpenCV device 0")
            else:
                try: cap.release()
                except Exception: pass
                cap = None
        except Exception:
            cap = None

    # create unix socket and listen for one client
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(socket_path)
    server.listen(1)
    server.settimeout(0.1)
    print(f"camera_service: listening on {socket_path}")

    client = None
    last_client_accept = 0.0
    target_dt = 1.0 / max(5.0, min(target_fps, 60.0))

    try:
        while True:
            t0 = time.time()
            # accept client if needed (non-blocking)
            if client is None:
                try:
                    client, _ = server.accept()
                    client.setblocking(True)
                    print("camera_service: client connected")
                except socket.timeout:
                    pass
                except Exception:
                    pass

            # capture frame
            frame = None
            try:
                if picam:
                    frame = picam.capture_array()
                elif cap:
                    ret, f = cap.read()
                    if ret:
                        frame = f
                if frame is None:
                    time.sleep(target_dt)
                    continue
            except Exception:
                time.sleep(target_dt)
                continue

            # small enhancement
            try:
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                l = clahe.apply(l)
                lab = cv2.merge([l, a, b])
                frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            except Exception:
                pass

            h, w = frame.shape[:2]
            roi_w = int(w * ROI_SCALE)
            roi_h = int(roi_w * 9 / 16)
            x_start = (w - roi_w) // 2
            y_start = (h - roi_h) // 2
            x_end = x_start + roi_w
            y_end = y_start + roi_h

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                res = hands.process(rgb)
            except Exception:
                res = None

            tips = []
            if getattr(res, "multi_hand_landmarks", None):
                for idx, hand_landmarks in enumerate(res.multi_hand_landmarks):
                    tip = hand_landmarks.landmark[8]
                    pip = hand_landmarks.landmark[6]
                    # permissive extension test (helps at distance)
                    ext = math.hypot(tip.x - pip.x, tip.y - pip.y) > 0.02
                    x_tip = int(tip.x * w)
                    y_tip = int(tip.y * h)
                    if x_start <= x_tip <= x_end and y_start <= y_tip <= y_end and ext:
                        rel_x = (min(max(x_tip, x_start), x_end) - x_start) / max(1, roi_w)
                        rel_y = (min(max(y_tip, y_start), y_end) - y_start) / max(1, roi_h)
                        # map into fixed projector space (1920x1080)
                        proj_x = int(rel_x * 1920)
                        proj_y = int(rel_y * 1080)
                        tips.append({"screen": (proj_x, proj_y), "hand_idx": idx})

            # send tips as one JSON line if client connected
            if client:
                try:
                    payload = json.dumps({"ts": time.time(), "tips": tips}) + "\n"
                    client.sendall(payload.encode("utf-8"))
                except Exception:
                    try:
                        client.close()
                    except Exception:
                        pass
                    client = None

            elapsed = time.time() - t0
            to_sleep = max(0.0, target_dt - elapsed)
            time.sleep(to_sleep)

    finally:
        try:
            server.close()
        except Exception:
            pass
        if picam:
            try: picam.stop()
            except Exception: pass
        if cap:
            try: cap.release()
            except Exception: pass

if __name__ == "__main__":
    main()