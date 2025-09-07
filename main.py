import pygame
import sys
import os
import time
from constants import init_fonts
from video_manager import VideoManager
from network_client import RemoteCameraClient
from hand_tracker import create_default_hand_tracker

USE_REMOTE = True
SERVER_URI = "ws://192.168.1.79:8765"

def main():
    """Main function to initialize and run the game selector"""
    pygame.init()
    init_fonts()

    # Now import game_selection (after fonts are initialized)
    from game_selection import show_game_selection

    screen_info = pygame.display.Info()
    screen_width, screen_height = screen_info.current_w, screen_info.current_h
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
    pygame.display.set_caption("Tabletop Game Selector")

    video_manager = VideoManager()
    video_path = os.path.join(os.path.dirname(__file__), "background_video.mp4")
    video_loaded = video_manager.load_video(video_path)

    net_client = None
    hand_tracker = None
    camera_source = None

    # Start remote client first (it should try USB OpenCV devices first).
    remote_client = None
    if USE_REMOTE:
        try:
            remote_client = RemoteCameraClient(server_uri=SERVER_URI)
            remote_client.start()
        except Exception:
            remote_client = None

    # Only start local tracker when not using remote camera (avoids camera contention)
    hand_tracker = None
    if not USE_REMOTE:
        try:
            hand_tracker = create_default_hand_tracker()
            hand_tracker.start()
        except Exception:
            hand_tracker = None

    try:
        # show_game_selection expects hand_tracker-like object (get_tips/get_primary)
        running = show_game_selection(screen, video_manager if video_loaded else None, hand_tracker=camera_source)
    finally:
        if net_client is not None:
            try:
                net_client.stop()
            except Exception:
                pass
        if hand_tracker is not None:
            try:
                hand_tracker.stop()
            except Exception:
                pass
        pygame.quit()

    if not running:
        sys.exit()

if __name__ == "__main__":
    main()