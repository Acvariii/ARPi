import cv2
import mediapipe as mp
import pyautogui
import math

# Get screen size
screen_w, screen_h = pyautogui.size()

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=16,
    min_detection_confidence=0.7
)

# Hand colors
colors = [
    (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 165, 0)
]

# Distance helper
def distance(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)

# Open Pi Camera
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape

    # Define smaller ROI (e.g., 70% of width/height, but still 16:9)
    roi_w = int(w * 0.7)
    roi_h = int(roi_w * 9 / 16)
    x_start = (w - roi_w) // 2
    y_start = (h - roi_h) // 2
    x_end, y_end = x_start + roi_w, y_start + roi_h

    # Convert full frame to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    # Draw ROI rectangle
    cv2.rectangle(frame, (x_start, y_start), (x_end, y_end), (200, 200, 200), 2)

    if result.multi_hand_landmarks:
        for idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
            color = colors[idx % len(colors)]

            # Get key landmarks
            tip = hand_landmarks.landmark[8]
            pip = hand_landmarks.landmark[6]
            mcp = hand_landmarks.landmark[5]

            # Check if finger is extended (orientation independent)
            extended = distance(tip, pip) > distance(pip, mcp) * 0.8

            # Convert to pixel coords
            x_tip = int(tip.x * w)
            y_tip = int(tip.y * h)

            if extended:
                cv2.circle(frame, (x_tip, y_tip), 15, color, 3)

                # Clamp fingertip inside ROI
                x_clamped = min(max(x_tip, x_start), x_end)
                y_clamped = min(max(y_tip, y_start), y_end)

                # Normalize relative to ROI
                rel_x = (x_clamped - x_start) / roi_w
                rel_y = (y_clamped - y_start) / roi_h

                # Map to screen
                screen_x = int(rel_x * screen_w)
                screen_y = int(rel_y * screen_h)

                if idx == 0:  # first hand controls cursor
                    pyautogui.moveTo(screen_x, screen_y)

    cv2.imshow("Hand Tracking Cursor (Smaller ROI + Any Orientation)", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
        break

cap.release()
cv2.destroyAllWindows()
