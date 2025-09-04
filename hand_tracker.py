import cv2
import mediapipe as mp
import pyautogui
import math
from picamera2 import Picamera2

# -----------------------
# Setup
# -----------------------
screen_w, screen_h = pyautogui.size()

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=16,
    min_detection_confidence=0.7
)

# Hand colors for multiple hands
colors = [
    (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 165, 0)
]

# Helper: 3D distance between landmarks
def distance(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)

# -----------------------
# Initialize Camera
# -----------------------
picam2 = Picamera2()
picam2.start()

# -----------------------
# Parameters
# -----------------------
roi_scale = 0.7  # scale of ROI relative to frame (0-1)

# -----------------------
# Main Loop
# -----------------------
while True:
    frame = picam2.capture_array()
    h, w, _ = frame.shape

    # -------------------
    # Define smaller ROI
    # -------------------
    roi_w = int(w * roi_scale)
    roi_h = int(roi_w * 9 / 16)  # maintain 16:9
    x_start = (w - roi_w) // 2
    y_start = (h - roi_h) // 2
    x_end, y_end = x_start + roi_w, y_start + roi_h

    # -------------------
    # Process frame with MediaPipe
    # -------------------
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    # Draw ROI rectangle
    cv2.rectangle(frame, (x_start, y_start), (x_end, y_end), (200, 200, 200), 2)

    # -------------------
    # Draw hands and control cursor
    # -------------------
    if result.multi_hand_landmarks:
        for idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
            color = colors[idx % len(colors)]

            tip = hand_landmarks.landmark[8]
            pip = hand_landmarks.landmark[6]
            mcp = hand_landmarks.landmark[5]

            # Orientation-independent index finger detection
            extended = distance(tip, pip) > distance(pip, mcp) * 0.8

            # Convert tip to pixel coordinates
            x_tip = int(tip.x * w)
            y_tip = int(tip.y * h)

            if extended:
                # Draw fingertip circle
                cv2.circle(frame, (x_tip, y_tip), 15, color, 3)

                # Clamp to ROI for cursor mapping
                x_clamped = min(max(x_tip, x_start), x_end)
                y_clamped = min(max(y_tip, y_start), y_end)

                # Normalize relative to ROI
                rel_x = (x_clamped - x_start) / roi_w
                rel_y = (y_clamped - y_start) / roi_h

                # Map to screen coordinates
                screen_x = int(rel_x * screen_w)
                screen_y = int(rel_y * screen_h)

                # First hand controls cursor
                if idx == 0:
                    pyautogui.moveTo(screen_x, screen_y)

    # -------------------
    # Show camera frame
    # -------------------
    cv2.imshow("Hand Tracking Cursor (Picamera2 + ROI)", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
        break

# -----------------------
# Cleanup
# -----------------------
cv2.destroyAllWindows()
picam2.stop()
