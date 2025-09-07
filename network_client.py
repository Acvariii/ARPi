import asyncio
import threading
import json
import time
import cv2
import numpy as np
import pygame
try:
    from picamera2 import Picamera2
except Exception:
    Picamera2 = None

SERVER_URI = "ws://192.168.1.79:8765"  # << replace with your Windows IP
# Lower quality + resize to reduce round-trip time and CPU on server
JPEG_QUALITY = 60
FPS = 60.0
SEND_WIDTH = 640

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
        # Always try USB OpenCV device first (even if Picamera2 is available).
        try:
            cap = cv2.VideoCapture(self.usb_index)
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, int(self._fps))
            except Exception:
                pass
            ret, _ = cap.read()
            if ret:
                self._cap = cap
                print("network_client: using USB camera (index {})".format(self.usb_index))
                return
            else:
                try:
                    cap.release()
                except Exception:
                    pass
                print("network_client: USB camera not available/failed initial read")
        except Exception as e:
            print(f"network_client: USB open error: {e}")
            self._cap = None

        # If no USB camera, try Picamera2 (Raspberry Pi camera) as fallback
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

        # final fallback: try default OpenCV device 0
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

                # receiver task: continuously read server messages and update tips immediately
                async def _recv_loop():
                    try:
                        while self._running:
                            msg = await ws.recv()
                            if isinstance(msg, (bytes, bytearray)):
                                try:
                                    text = msg.decode('utf-8', errors='ignore')
                                    data = json.loads(text)
                                except Exception:
                                    continue
                            else:
                                try:
                                    data = json.loads(msg)
                                except Exception:
                                    continue
                            tips = data.get("tips", [])
                            with self._lock:
                                self._latest_tips = tips
                            # Post a pygame event so the main UI can react immediately
                            try:
                                if pygame.get_init():
                                    ev = pygame.event.Event(pygame.USEREVENT + 1, {"tips": tips})
                                    pygame.event.post(ev)
                            except Exception:
                                pass
                            if tips:
                                # debug log - helps verify server -> client tip flow
                                print(f"network_client: received {len(tips)} tips, first screen={tips[0].get('screen')}")
                    except Exception as e:
                        # receiver exiting (connection closed or error)
                        print(f"network_client: recv loop ended: {e}")

                recv_task = asyncio.create_task(_recv_loop())

                # sender loop: capture frames and send continuously, does not wait for replies
                while self._running:
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

                    # Resize down (preserve aspect) to reduce network + server load
                    try:
                        h, w = frame.shape[:2]
                        if w > SEND_WIDTH:
                            new_h = int(SEND_WIDTH * (h / max(1, w)))
                            frame_send = cv2.resize(frame, (SEND_WIDTH, new_h), interpolation=cv2.INTER_LINEAR)
                        else:
                            frame_send = frame
                    except Exception:
                        frame_send = frame

                    # encode JPEG and send (best-effort)
                    try:
                        _, jpg = cv2.imencode('.jpg', frame_send, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                        await ws.send(jpg.tobytes())
                    except Exception as e:
                        print(f"network_client: send error: {e}")
                        break

                    # pace the loop to target FPS
                    await asyncio.sleep(interval)

                # clean up receiver if still running
                if not recv_task.done():
                    recv_task.cancel()
                    try:
                        await recv_task
                    except Exception:
                        pass
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