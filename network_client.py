import asyncio
import threading
import json
import time
import cv2
import numpy as np
try:
    from picamera2 import Picamera2
except Exception:
    Picamera2 = None

SERVER_URI = "ws://192.168.1.79:8765"  # << replace with your Windows IP
JPEG_QUALITY = 70
FPS = 30.0

class RemoteCameraClient:
    def __init__(self, server_uri=SERVER_URI, usb_index=0, prefer_usb=True, fps=FPS):
        self.server_uri = server_uri
        self.usb_index = usb_index
        self.prefer_usb = prefer_usb
        self._cap = None
        self._picam = None
        self._running = False
        self._thread = None
        self._lock = threading.RLock()
        self._latest_tips = []
        self._fps = fps

    def _open_camera(self):
        # try USB first
        if self.prefer_usb:
            try:
                cap = cv2.VideoCapture(self.usb_index)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, int(self._fps))
                ret, _ = cap.read()
                if ret:
                    self._cap = cap
                    print("network_client: using USB camera (index {})".format(self.usb_index))
                    return
                else:
                    try: cap.release()
                    except Exception: pass
                    print("network_client: USB camera not available/failed initial read")
            except Exception as e:
                print(f"network_client: USB open error: {e}")
                self._cap = None

        # fallback to Picamera2
        if Picamera2 is not None:
            try:
                self._picam = Picamera2()
                try:
                    cfg = self._picam.create_preview_configuration(main={"size": (800,600)})
                except Exception:
                    cfg = self._picam.create_preview_configuration(main={"size": (640,480)})
                self._picam.configure(cfg)
                self._picam.start()
                print("network_client: using Picamera2")
                return
            except Exception as e:
                print(f"network_client: Picamera2 open error: {e}")
                self._picam = None

        # final fallback: default cv device 0
        try:
            self._cap = cv2.VideoCapture(0)
            ret, _ = self._cap.read()
            if ret:
                print("network_client: using fallback OpenCV device 0")
            else:
                print("network_client: fallback OpenCV device 0 failed initial read")
        except Exception as e:
            print(f"network_client: fallback camera error: {e}")
            self._cap = None

    def start(self):
        if self._running:
            return
        self._open_camera()
        self._running = True
        self._thread = threading.Thread(target=asyncio.run, args=(self._run_loop(),), daemon=True)
        self._thread.start()
        # give a moment to connect
        time.sleep(0.05)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._picam:
            try: self._picam.stop()
            except Exception: pass
            self._picam = None
        if self._cap:
            try: self._cap.release()
            except Exception: pass
            self._cap = None

    async def _run_loop(self):
        import websockets
        try:
            async with websockets.connect(self.server_uri, max_size=10_000_000) as ws:
                print(f"network_client: connected to {self.server_uri}")
                interval = 1.0 / max(1, self._fps)
                while self._running:
                    # capture
                    frame = None
                    if self._picam:
                        try:
                            frame = self._picam.capture_array()
                        except Exception:
                            frame = None
                    elif self._cap:
                        ret, f = self._cap.read()
                        if ret:
                            frame = f
                    if frame is None:
                        await asyncio.sleep(interval)
                        continue

                    # encode JPEG
                    try:
                        _, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                        await ws.send(jpg.tobytes())
                    except Exception as e:
                        print(f"network_client: send error: {e}")
                        break

                    # try to read a single JSON reply quickly (low timeout for responsiveness)
                    try:
                        resp = await asyncio.wait_for(ws.recv(), timeout=0.05)
                        # server sends JSON text
                        if isinstance(resp, (bytes, bytearray)):
                            resp = resp.decode('utf-8', errors='ignore')
                        data = json.loads(resp)
                        tips = data.get("tips", [])
                        with self._lock:
                            self._latest_tips = tips
                        # debug log - helps verify server -> client tip flow
                        if tips:
                            print(f"network_client: received {len(tips)} tips, first screen={tips[0].get('screen')}")
                    except asyncio.TimeoutError:
                        # no reply this frame, that's ok - continue to next capture
                        pass
                    except Exception as e:
                        print(f"network_client: recv error: {e}")
                        break

                    # pace the loop to target FPS
                    await asyncio.sleep(interval)
        except Exception as e:
            print(f"network_client: connection failed: {e}")

    def get_tips(self):
        with self._lock:
            return list(self._latest_tips)

    def get_primary(self):
        """Return first tip 'screen' coords or None (compatible with MultiHandTracker API)."""
        tips = self.get_tips()
        if not tips:
            return None
        pos = tips[0].get("screen")
        if pos is None:
            return None
        # ensure tuple of ints
        try:
            return (int(pos[0]), int(pos[1]))
        except Exception:
            return None

# usage:
# client = RemoteCameraClient(server_uri="ws://192.168.1.10:8765")
# client.start()
# tips = client.get_tips()
# client.stop()