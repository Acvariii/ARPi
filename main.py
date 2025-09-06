import pygame
import sys
import os
from constants import init_fonts
from video_manager import VideoManager
from network_client import RemoteCameraClient
from hand_tracker import MultiHandTracker

USE_REMOTE = True
SERVER_URI = "ws://192.168.1.79:8765"

def main():
    """Main function to initialize and run the game selector"""
    # Initialize pygame
    pygame.init()
    
    # Initialize fonts after pygame is initialized
    init_fonts()
    
    # Now import game_selection (after fonts are initialized)
    from game_selection import show_game_selection

    # Get screen info for fullscreen
    screen_info = pygame.display.Info()
    screen_width, screen_height = screen_info.current_w, screen_info.current_h
    
    # Set up the screen
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
    pygame.display.set_caption("Tabletop Game Selector")
    
    # Initialize video background
    video_manager = VideoManager()
    video_path = os.path.join(os.path.dirname(__file__), "background_video.mp4")
    video_loaded = video_manager.load_video(video_path)

    if USE_REMOTE:
        # start remote client and DO NOT start local MultiHandTracker (avoids camera contention)
        net_client = RemoteCameraClient(server_uri=SERVER_URI)
        net_client.start()
        camera_source = net_client
    else:
        # Initialize hand tracker (start immediately) with higher refresh + smoother rendering
        # prefer lower smoothing (more responsive), higher target_fps; tune to your Pi5 performance
        # Projector resolution is fixed: map camera tips into projector coordinates (1920x1080).
        # Pygame still uses the actual display resolution for rendering; the tracker always reports
        # tip coordinates in projector space so UI logic is stable.
        hand_tracker = MultiHandTracker(
            screen_size=(1920, 1080),   # fixed projector mapping
            max_hands=8,
            smoothing=0.60,
            target_fps=60,
            roi_scale=0.98
        )
        try:
            hand_tracker.start()
        except Exception:
            # ensure app still runs if camera unavailable
            pass
        camera_source = hand_tracker

    # Run the game selection screen
    try:
        running = show_game_selection(screen, video_manager if video_loaded else None, hand_tracker=camera_source)
    finally:
        # Clean up
        video_manager.release()
        if USE_REMOTE:
            net_client.stop()
        else:
            try:
                hand_tracker.stop()
            except Exception:
                pass
        pygame.quit()
    if not running:
        sys.exit()

if __name__ == "__main__":
    main()