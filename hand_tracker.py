# Simple Hand Tracking with Index Finger Bounding Box
# Directly reads from rpicam-vid stdout

import cv2
import mediapipe as mp
import subprocess
import numpy as np
import time
import signal
import sys

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('Shutting down...')
    cv2.destroyAllWindows()
    sys.exit(0)

def main():
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize MediaPipe
    mp_drawing = mp.solutions.drawing_utils
    mp_hands = mp.solutions.hands
    
    # Start rpicam-vid process
    command = [
        'rpicam-vid',
        '-t', '0',           # Run indefinitely
        '--width', '640',    # Width
        '--height', '480',   # Height
        '--framerate', '15', # Framerate
        '--nopreview',       # No preview window
        '--codec', 'mjpeg',  # Use MJPEG format
        '-o', '-'            # Output to stdout
    ]
    
    print("Starting camera process...")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Allow time for camera to start
    time.sleep(2)
    
    print("Camera started. Press 'Q' to quit.")
    
    # Initialize variables
    frame_count = 0
    start_time = time.time()
    fps = 0
    box_size = 80
    
    with mp_hands.Hands(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        max_num_hands=2) as hands:
        
        while True:
            # Read JPEG data from stdout
            jpeg_data = process.stdout.read(1024 * 1024)  # Read up to 1MB
            
            if not jpeg_data:
                print("No data from camera. Exiting.")
                break
            
            # Convert JPEG data to numpy array
            nparr = np.frombuffer(jpeg_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                continue
            
            # Flip frame horizontally for a mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame with MediaPipe
            results = hands.process(frame_rgb)
            
            # Check if index finger is detected
            finger_detected = False
            cx, cy = 0, 0
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Get index finger tip coordinates
                    h, w, _ = frame.shape
                    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    cx, cy = int(index_finger_tip.x * w), int(index_finger_tip.y * h)
                    
                    # Draw bounding box
                    x1 = max(0, cx - box_size // 2)
                    y1 = max(0, cy - box_size // 2)
                    x2 = min(w, cx + box_size // 2)
                    y2 = min(h, cy + box_size // 2)
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.circle(frame, (cx, cy), 10, (0, 255, 0), -1)
                    
                    finger_detected = True
            
            # Display FPS
            frame_count += 1
            elapsed_time = time.time() - start_time
            if elapsed_time > 1:
                fps = frame_count / elapsed_time
                frame_count = 0
                start_time = time.time()
            
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Display status
            status = "Finger: Detected" if finger_detected else "Finger: Not Detected"
            cv2.putText(frame, status, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if finger_detected else (0, 0, 255), 2)
            
            # Display instructions
            cv2.putText(frame, "Press 'Q' to quit", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Show the frame
            cv2.imshow('Index Finger Tracking', frame)
            
            # Check for quit command
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    # Clean up
    process.terminate()
    cv2.destroyAllWindows()
    print("Application closed.")

if __name__ == "__main__":
    main()