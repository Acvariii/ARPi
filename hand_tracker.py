import cv2
import mediapipe as mp

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=16, min_detection_confidence=0.6)
mp_draw = mp.solutions.drawing_utils

# Open Pi Camera (0 = default camera, adjust if needed)
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Convert BGR (OpenCV) to RGB (MediaPipe)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            h, w, _ = frame.shape

            # Index finger tip and lower joint
            x_tip = int(hand_landmarks.landmark[8].x * w)
            y_tip = int(hand_landmarks.landmark[8].y * h)
            y_lower = int(hand_landmarks.landmark[6].y * h)

            # Check if finger is raised (tip is higher than lower joint)
            if y_tip < y_lower:
                cv2.circle(frame, (x_tip, y_tip), 15, (0, 255, 0), 3)

    cv2.imshow("Index Finger Tracking", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC key to quit
        break

cap.release()
cv2.destroyAllWindows()
