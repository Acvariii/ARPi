import pygame
import cv2
import numpy as np
import os

class VideoManager:
    """Manages video background playback using OpenCV"""

    def __init__(self):
        self.cap = None
        self.video_size = (0, 0)
        self.initialized = False

    def load_video(self, video_path):
        """Load a video file for background playback"""
        if os.path.exists(video_path):
            try:
                self.cap = cv2.VideoCapture(video_path)
                if self.cap.isOpened():
                    self.video_size = (
                        int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    )
                    self.initialized = True
                    print("Video background loaded successfully")
                    return True
            except Exception as e:
                print(f"Error loading video: {e}")
        return False

    def update_frame(self, screen):
        """Update and draw the current video frame to the screen"""
        if not self.initialized:
            return False

        try:
            ret, frame = self.cap.read()
            if not ret:
                # Loop the video
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    return False

            # Convert BGR to RGB and rotate for Pygame
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.rot90(frame)
            frame_surface = pygame.surfarray.make_surface(frame)

            # Scale to fit screen while maintaining aspect ratio
            screen_size = screen.get_size()
            video_ratio = self.video_size[0] / max(1, self.video_size[1])
            screen_ratio = screen_size[0] / max(1, screen_size[1])

            if video_ratio > screen_ratio:
                scale_height = screen_size[1]
                scale_width = int(scale_height * video_ratio)
                scaled_frame = pygame.transform.scale(frame_surface, (scale_width, scale_height))
                x_offset = (scale_width - screen_size[0]) // 2
                screen.blit(scaled_frame, (-x_offset, 0))
            else:
                scale_width = screen_size[0]
                scale_height = int(scale_width / max(0.0001, video_ratio))
                scaled_frame = pygame.transform.scale(frame_surface, (scale_width, scale_height))
                y_offset = (scale_height - screen_size[1]) // 2
                screen.blit(scaled_frame, (0, -y_offset))

            return True

        except Exception as e:
            print(f"Error updating video frame: {e}")
            return False

    def release(self):
        """Release video resources"""
        if self.cap:
            self.cap.release()
        self.initialized = False

def create_overlay(screen_size, color=(25, 25, 35), alpha=200):
    """Create a semi-transparent overlay for better text readability"""
    overlay = pygame.Surface(screen_size, pygame.SRCALPHA)
    overlay.fill((*color, alpha))
    return overlay