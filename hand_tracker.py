import cv2
import mediapipe as mp
import pyautogui
import math
import numpy as np
from picamera2 import Picamera2

# -----------------------
# Screen setup
# -----------------------
screen_w, screen_h = pyautogui.size()

# -----------------------
# MediaPipe Hands
# -----------------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=16,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.6
)

colors = [
    (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 165, 0)
]

def distance(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)

# -----------------------
# Camera setup
# -----------------------
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (800, 600)})
picam2.configure(config)

# Low-light settings
picam2.set_controls({
    "ExposureTime": 25000,
    "AnalogueGain": 4.0,
    "Brightness": 0.3
})
picam2.start()

# ROI
roi_scale = 0.8

# -----------------------
# Frame preprocessing
# -----------------------
def enhance_frame(frame):
    # Keep RGB; apply CLAHE + gamma on each channel
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    # Gamma correction
    gamma = 1.3
    lookUpTable = np.array([((i/255.0)**(1.0/gamma))*255 for i in np.arange(0,256)]).astype("uint8")
    return cv2.LUT(frame, lookUpTable)

# -----------------------
# Main loop
# -----------------------
while True:
    frame = picam2.capture_array()
    frame = enhance_frame(frame)
    h, w, _ = frame.shape

    # ROI
    roi_w = int(w * roi_scale)
    roi_h = int(roi_w * 9 / 16)
    x_start = (w - roi_w) // 2
    y_start = (h - roi_h) // 2
    x_end, y_end = x_start + roi_w, y_start + roi_h

    # -------------------
    # MediaPipe detection (full frame)
    # -------------------
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    # Draw ROI rectangle
    cv2.rectangle(frame, (x_start, y_start), (x_end, y_end), (200,200,200), 2)

    # Hand tracking & cursor mapping
    if result.multi_hand_landmarks:
        for idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
            color = colors[idx % len(colors)]
            tip = hand_landmarks.landmark[8]
            pip = hand_landmarks.landmark[6]
            mcp = hand_landmarks.landmark[5]

            extended = distance(tip, pip) > distance(pip, mcp) * 0.8

            x_tip = int(tip.x * w)
            y_tip = int(tip.y * h)

            # Only map hands inside the ROI
            if x_start <= x_tip <= x_end and y_start <= y_tip <= y_end and extended:
                cv2.circle(frame, (x_tip, y_tip), 15, color, 3)

                # Clamp to ROI
                x_clamped = min(max(x_tip, x_start), x_end)
                y_clamped = min(max(y_tip, y_start), y_end)

                rel_x = (x_clamped - x_start) / roi_w
                rel_y = (y_clamped - y_start) / roi_h

                screen_x = int(rel_x * screen_w)
                screen_y = int(rel_y * screen_h)

                # First hand controls cursor
                if idx == 0:
                    pyautogui.moveTo(screen_x, screen_y)

    # Display
    cv2.imshow("Hand Tracking - Full Color ROI", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cv2.destroyAllWindows()
picam2.stop()
