import asyncio
import json
import time
import math
import cv2
import numpy as np
import mediapipe as mp
import websockets

# Simple WebSocket server: receive JPEG frames (binary), return JSON tips.
HOST = "192.168.1.79"
PORT = 8765
PROJECTOR_W, PROJECTOR_H = 1920, 1080  # change if needed

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=8, min_detection_confidence=0.45, min_tracking_confidence=0.5)

async def handle(ws, path):
    async for msg in ws:
        # Expect binary JPEG frames
        if isinstance(msg, bytes):
            nparr = np.frombuffer(msg, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                continue
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                res = hands.process(rgb)
            except Exception:
                res = None

            tips = []
            if getattr(res, "multi_hand_landmarks", None):
                for idx, lm in enumerate(res.multi_hand_landmarks):
                    tip = lm.landmark[8]
                    pip = lm.landmark[6]
                    ext = math.hypot(tip.x - pip.x, tip.y - pip.y) > 0.02
                    x_tip = int(tip.x * w)
                    y_tip = int(tip.y * h)
                    if ext:
                        # map to projector coordinates (optional)
                        proj_x = int(tip.x * PROJECTOR_W)
                        proj_y = int(tip.y * PROJECTOR_H)
                        tips.append({"hand_idx": idx, "roi": (x_tip, y_tip), "screen": (proj_x, proj_y)})

            payload = json.dumps({"ts": time.time(), "tips": tips})
            try:
                await ws.send(payload)
            except Exception:
                return

async def main():
    async with websockets.serve(handle, HOST, PORT, max_size=10_000_000):
        print(f"server: listening on ws://{HOST}:{PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())