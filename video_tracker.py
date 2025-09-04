# Hand Tracking with MediaPipe on Raspberry Pi
# Enhanced with better error handling and camera diagnostics

import cv2
import mediapipe as mp
import time
import sys

def check_camera():
    """Check available cameras and return the first working one"""
    # Test cameras from index 0 to 4
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"Camera found at index {i}")
                cap.release()
                return i
            cap.release()
    return -1

def main():
    # Initialize MediaPipe Hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    mp_hands = mp.solutions.hands

    # Find a working camera
    camera_index = check_camera()
    if camera_index == -1:
        print("Error: No working camera found.")
        print("Please check your camera connection and try again.")
        return

    # Initialize camera
    cap = cv2.VideoCapture(camera_index)
    
    # Allow camera to warm up
    time.sleep(2.0)
    
    # Set camera resolution for Raspberry Pi compatibility
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        print("Make sure your camera is connected and not being used by another application.")
        return

    print("Camera opened successfully. Press 'Q' to quit.")

    with mp_hands.Hands(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        max_num_hands=2) as hands:
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            # Read frame from camera
            ret, frame = cap.read()
            
            # Check if frame was read successfully
            if not ret or frame is None:
                print("Failed to grab frame. Trying to reconnect...")
                cap.release()
                time.sleep(1)  # Wait a bit before trying again
                
                # Try to reconnect to camera
                cap = cv2.VideoCapture(camera_index)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                time.sleep(1)  # Allow camera to initialize
                continue
            
            # Resize frame if it's not empty
            try:
                frame = cv2.resize(frame, (640, 480))
            except Exception as e:
                print(f"Error resizing frame: {e}")
                continue
            
            # Convert the BGR image to RGB
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the image and detect hands
            results = hands.process(image_rgb)
            
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
            if elapsed_time > 1:  # Update FPS every second
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

    cap.release()
    cv2.destroyAllWindows()
    print("Application closed.")

if __name__ == "__main__":
    main()