# Hand Tracking with MediaPipe for Raspberry Pi AI Camera
# Using OpenCV instead of Picamera2 to avoid dependency issues

import cv2
import mediapipe as mp
import time

def main():
    # Initialize MediaPipe
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    mp_hands = mp.solutions.hands
    
    # Initialize camera - try different indices
    camera = None
    for i in range(4):  # Try cameras 0 to 3
        camera = cv2.VideoCapture(i)
        if camera.isOpened():
            ret, frame = camera.read()
            if ret:
                print(f"Found camera at index {i}")
                break
            else:
                camera.release()
                camera = None
        else:
            camera = None
    
    if camera is None:
        print("Error: Could not find any camera")
        return
    
    # Set camera properties
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 30)
    
    # Allow camera to initialize
    time.sleep(2)
    
    print("Camera started. Press 'Q' to quit.")
    
    # FPS calculation variables
    frame_count = 0
    start_time = time.time()
    fps = 0
    
    with mp_hands.Hands(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        max_num_hands=2) as hands:
        
        while True:
            # Capture frame
            ret, frame = camera.read()
            if not ret:
                print("Failed to grab frame")
                break
            
            # Flip frame horizontally for a mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame with MediaPipe
            results = hands.process(frame_rgb)
            
            # Draw hand landmarks if detected
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style())
                    
                    # Get index finger tip coordinates (landmark 8)
                    h, w, _ = frame.shape
                    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    cx, cy = int(index_finger_tip.x * w), int(index_finger_tip.y * h)
                    
                    # Draw a circle on the index finger tip
                    cv2.circle(frame, (cx, cy), 10, (0, 255, 0), -1)
                    
                    # Display coordinates
                    cv2.putText(frame, f"Index: ({cx}, {cy})", (cx-50, cy-20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Calculate and display FPS
            frame_count += 1
            elapsed_time = time.time() - start_time
            if elapsed_time > 1:
                fps = frame_count / elapsed_time
                frame_count = 0
                start_time = time.time()
            
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Display instructions
            cv2.putText(frame, "Press 'Q' to quit", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Show the frame
            cv2.imshow('MediaPipe Hands - Raspberry Pi', frame)
            
            # Check for quit command
            if cv2.waitKey(5) & 0xFF == ord('q'):
                break
    
    # Clean up
    camera.release()
    cv2.destroyAllWindows()
    print("Application closed.")

if __name__ == "__main__":
    main()