import pygame
import sys
import os
from constants import init_fonts
from video_manager import VideoManager

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

    # Run the game selection screen
    try:
        running = show_game_selection(screen, video_manager if video_loaded else None)
    finally:
        # Clean up
        video_manager.release()
        pygame.quit()
    if not running:
        sys.exit()

if __name__ == "__main__":
    main()