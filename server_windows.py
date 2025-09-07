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
# Use lower model_complexity for faster, lower-latency inference on the Windows server.
# Keep min_detection_confidence/tracking_confidence the same to preserve behaviour.
hands = mp_hands.Hands(
    max_num_hands=8,
    model_complexity=0,
    min_detection_confidence=0.45,
    min_tracking_confidence=0.5
)

async def handle(ws, path=None):
    # support both websockets versions: path may be passed or available on the protocol
    path = path or getattr(ws, "path", None)
    # announce connection
    try:
        peer = getattr(ws, "remote_address", None)
    except Exception:
        peer = None
    peer_str = str(peer) if peer is not None else "client"
    win_name = f"client_video_{peer_str}"
    print(f"server: client connected (peer={peer}, path={path})")
    saw_video = False
    last_tips_announce = 0.0
    last_tips = []
    try:
        # create window for this client
        try:
            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        except Exception:
            pass

        async for msg in ws:
            # Expect binary JPEG frames
            if isinstance(msg, bytes):
                if not saw_video:
                    saw_video = True
                    print("server: receiving video stream from client")
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
                            proj_x = int(tip.x * PROJECTOR_W)
                            proj_y = int(tip.y * PROJECTOR_H)
                            tips.append({"hand_idx": idx, "roi": (x_tip, y_tip), "screen": (proj_x, proj_y)})
                            # draw circle on frame around index tip
                            try:
                                cv2.circle(frame, (x_tip, y_tip), max(6, int(min(w,h)*0.03)), (0,255,0), 2)
                                cv2.circle(frame, (x_tip, y_tip), max(2, int(min(w,h)*0.01)), (0,255,0), -1)
                            except Exception:
                                pass

                # update last_tips for periodic announcements
                last_tips = tips
                now = time.time()
                if now - last_tips_announce >= 5.0:
                    last_tips_announce = now
                    if tips:
                        locs = [t.get("screen") or t.get("roi") for t in tips]
                        print(f"server: index-tip locations (every-5s): {locs}")
                    else:
                        print("server: no tips detected in last 5s")

                # show the frame for this client
                try:
                    cv2.imshow(win_name, frame)
                    # required to update window events; value small to be non-blocking
                    cv2.waitKey(1)
                except Exception:
                    pass

                payload = json.dumps({"ts": time.time(), "tips": tips})
                try:
                    await ws.send(payload)
                except Exception:
                    return
            else:
                # ignore non-binary messages but log occasionally
                try:
                    text = msg if isinstance(msg, str) else str(msg)
                    if text and len(text) < 200:
                        print(f"server: received text message from client: {text}")
                except Exception:
                    pass
    except websockets.ConnectionClosed:
        pass
    finally:
        # destroy window on disconnect
        try:
            cv2.destroyWindow(win_name)
        except Exception:
            pass
        print(f"server: client disconnected (peer={peer})")
        return

async def main():
    async with websockets.serve(handle, HOST, PORT, max_size=10_000_000):
        print(f"server: listening on ws://{HOST}:{PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())