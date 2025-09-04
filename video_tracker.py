# Hand Tracking using rpicam-vid stream
# This approach uses rpicam-vid to capture video and pipe it to OpenCV

import cv2
import mediapipe as mp
import subprocess
import numpy as np
import time

def main():
    # Initialize MediaPipe
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    mp_hands = mp.solutions.hands
    
    # Start rpicam-vid process
    command = [
        'rpicam-vid',
        '-t', '0',           # Run indefinitely
        '--width', '640',    # Width
        '--height', '480',   # Height
        '--framerate', '30', # Framerate
        '-o', '-'            # Output to stdout
    ]
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=10**8
    )
    
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
            # Read frame from rpicam-vid output
            # This is a simplified approach - in practice you'd need to parse the stream properly
            raw_frame = process.stdout.read(640 * 480 * 3)
            if len(raw_frame) != 640 * 480 * 3:
                continue
                
            # Convert to numpy array
            frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((480, 640, 3))
            
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
    process.terminate()
    cv2.destroyAllWindows()
    print("Application closed.")

if __name__ == "__main__":
    main()