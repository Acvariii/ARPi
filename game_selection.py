import pygame
import sys
import time
from ui_components import draw_button, draw_hover_timer
from constants import FONT_LARGE, FONT_MEDIUM, TEXT_COLOR, GAMES

def update_video_background(screen, video_manager):
    """Update and draw the video background using VideoManager"""
    if not video_manager or not video_manager.initialized:
        return False
    
    try:
        return video_manager.update_frame(screen)
    except Exception as e:
        print(f"Error updating video background: {e}")
        return False

def show_game_selection(screen, video_manager=None, hand_tracker=None):
    """Display the main game selection screen with video background"""
    clock = pygame.time.Clock()
    button_width, button_height = 300, 80
    button_margin = 40
    total_height = len(GAMES) * button_height + (len(GAMES) - 1) * button_margin
    start_y = (screen.get_height() - total_height) // 2

    hover_start_time = 0
    hovered_button = None

    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((25, 25, 35, 200))  # Semi-transparent dark background

    running = True
    while running:
        # prefer hand tracker primary tip; fallback to mouse
        primary = None
        tips = []
        if hand_tracker:
            try:
                # get_primary still useful for hover logic; get_tips used for rendering visible cursors
                primary = hand_tracker.get_primary()
                tips = hand_tracker.get_tips()
            except Exception:
                primary = None
                tips = []
        mouse_pos = primary if primary is not None else pygame.mouse.get_pos()
        current_time = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False

        if video_manager and getattr(video_manager, "initialized", False):
            try:
                video_manager.update_frame(screen)
            except Exception:
                screen.fill((25, 25, 35))
        else:
            screen.fill((25, 25, 35))

        screen.blit(overlay, (0, 0))

        # draw fingertip indicators from the tracker (so you see the circle on the projected table)
        try:
            for tip in tips:
                # tip["screen"] is (x, y) mapped to projector/screen coordinates
                pos = tip.get("screen")
                if pos:
                    # outer ring + inner dot for good visibility
                    pygame.draw.circle(screen, (0, 0, 0), pos, 16, 4)
                    pygame.draw.circle(screen, (60, 220, 80), pos, 10)
        except Exception:
            pass

        selected_game = None
        for i, game in enumerate(GAMES):
            button_x = screen.get_width() // 2 - button_width // 2
            button_y = start_y + i * (button_height + button_margin)
            button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

            if button_rect.collidepoint(mouse_pos):
                if hovered_button != i:
                    hovered_button = i
                    hover_start_time = current_time
                if current_time - hover_start_time >= 1.0:
                    selected_game = game
                    break
            else:
                if hovered_button == i:
                    hovered_button = None

        if selected_game:
            from player_selection import show_game_player_selection
            show_game_player_selection(screen, selected_game, video_manager, hand_tracker=hand_tracker)
            hovered_button = None

        title = FONT_LARGE.render("ARPi Game Selector", True, TEXT_COLOR)
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 50))

        for i, game in enumerate(GAMES):
            button_x = screen.get_width() // 2 - button_width // 2
            button_y = start_y + i * (button_height + button_margin)
            button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            is_hovering = button_rect.collidepoint(mouse_pos)
            draw_button(screen, button_x, button_y, button_width, button_height, game["name"], is_hovering)
            if is_hovering and hovered_button == i:
                hover_time = current_time - hover_start_time
                # draw hover timer where appropriate
                draw_hover_timer(screen, mouse_pos, hover_time)

        # draw fingertip indicators last so they appear on top of all UI
        try:
            for tip in tips:
                pos = tip.get("screen")
                if pos:
                    pygame.draw.circle(screen, (0, 0, 0), pos, 16, 4)
                    pygame.draw.circle(screen, (60, 220, 80), pos, 10)
        except Exception:
            pass

        instructions = FONT_MEDIUM.render("• Hover over a game to select •", True, TEXT_COLOR)
        screen.blit(instructions, (screen.get_width() // 2 - instructions.get_width() // 2, screen.get_height() - 80))

        pygame.display.flip()
        clock.tick(60)
    return True