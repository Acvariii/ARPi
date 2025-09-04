import pygame
import sys
import time
from ui_components import draw_button, draw_hover_timer
from game_utils import get_player_positions, load_board_image
from constants import PLAYER_COLORS

def show_launch_confirmation(screen, game_name, num_players, video_manager=None):
    if video_manager and getattr(video_manager, "initialized", False):
        video_manager.update_frame(screen)
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((40, 40, 60, 220))
        screen.blit(overlay, (0, 0))
    else:
        screen.fill((40, 40, 60))

    font_large = pygame.font.SysFont("Arial", 48, bold=True)
    font_medium = pygame.font.SysFont("Arial", 36)
    title = font_large.render(game_name, True, (240, 240, 240))
    screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, screen.get_height() // 2 - 100))

    message = font_medium.render(f"Starting with {num_players} players", True, (240, 240, 240))
    screen.blit(message, (screen.get_width() // 2 - message.get_width() // 2, screen.get_height() // 2))

    loading = font_medium.render("Loading game...", True, (180, 180, 180))
    screen.blit(loading, (screen.get_width() // 2 - loading.get_width() // 2, screen.get_height() // 2 + 100))

    pygame.display.flip()
    pygame.time.wait(2000)

def launch_game(screen, game_name, num_players, video_manager=None, hand_tracker=None):
    try:
        if game_name.lower() == "monopoly":
            from monopoly import run_monopoly_game
            show_launch_confirmation(screen, game_name, num_players, video_manager)
            return run_monopoly_game(screen, num_players, video_manager, hand_tracker=hand_tracker)
        else:
            show_launch_confirmation(screen, game_name, num_players, video_manager)
            return True
    except Exception as e:
        print(f"Error launching game: {e}")
        return False

def draw_player_control_areas_preview(screen, num_players, game_x, game_y, game_width, game_height, board_shape):
    positions = get_player_positions(num_players, board_shape)
    sides = {
        "top": {"x": game_x, "y": 0, "width": game_width, "height": game_y},
        "right": {"x": game_x + game_width, "y": game_y, "width": screen.get_width() - (game_x + game_width), "height": game_height},
        "bottom": {"x": game_x, "y": game_y + game_height, "width": game_width, "height": screen.get_height() - (game_y + game_height)},
        "left": {"x": 0, "y": game_y, "width": game_x, "height": game_height}
    }
    side_counts = {"top": 0, "right": 0, "bottom": 0, "left": 0}
    for pos in positions:
        side_counts[pos] += 1

    for i, position in enumerate(positions):
        player_color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        side = sides[position]
        count_on_side = side_counts[position]
        player_index_on_side = positions[:i+1].count(position) - 1

        if position in ["top", "bottom"]:
            player_width = side["width"] // max(1, count_on_side)
            player_x = side["x"] + player_index_on_side * player_width
            player_y = side["y"]
            player_height = side["height"]
            pygame.draw.rect(screen, player_color, (player_x, player_y, player_width, player_height))
            pygame.draw.rect(screen, (min(255, player_color[0]+40), min(255, player_color[1]+40), min(255, player_color[2]+40)),
                             (player_x, player_y, player_width, player_height), width=3)
            action_width = (player_width - 40) // 3
            action_height = max(20, player_height - 30)
            for j in range(3):
                action_x = player_x + 20 + j * (action_width + 5)
                action_y = player_y + 15
                pygame.draw.rect(screen, (60, 60, 80), (action_x, action_y, action_width, action_height), border_radius=8)
        else:
            player_width = side["width"]
            player_height = side["height"] // max(1, count_on_side)
            player_x = side["x"]
            player_y = side["y"] + player_index_on_side * player_height
            pygame.draw.rect(screen, player_color, (player_x, player_y, player_width, player_height))
            pygame.draw.rect(screen, (min(255, player_color[0]+40), min(255, player_color[1]+40), min(255, player_color[2]+40)),
                             (player_x, player_y, player_width, player_height), width=3)
            action_width = max(20, player_width - 30)
            action_height = (player_height - 40) // 3
            for j in range(3):
                action_x = player_x + 15
                action_y = player_y + 20 + j * (action_height + 5)
                pygame.draw.rect(screen, (60, 60, 80), (action_x, action_y, action_width, action_height), border_radius=8)

def show_game_player_selection(screen, game, video_manager=None, hand_tracker=None):
    clock = pygame.time.Clock()
    selected_players = 2
    max_players = game["max_players"]
    board_shape = game["board_shape"]

    if board_shape == "square":
        game_width = screen.get_width() - 600
        game_height = screen.get_height() - 300
        game_x = 300
        game_y = 150
    else:
        game_width = screen.get_width() - 400
        game_height = screen.get_height() - 400
        game_x = 200
        game_y = 200

    hover_start_time = 0
    hovered_player_button = None
    hovered_button = None
    # exit-to-game-selection hover state
    exit_hover_start = None
    EXIT_HOVER_REQUIRED = 5.0  # seconds to hover to return to game selection

    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((25, 25, 35, 200))

    running = True
    while running:
        # prefer hand tracker primary tip; fallback to mouse
        primary = None
        tips = []
        if hand_tracker:
            try:
                primary = hand_tracker.get_primary()
                tips = hand_tracker.get_tips()
            except Exception:
                primary = None
                tips = []
        mouse_pos = primary if primary is not None else pygame.mouse.get_pos()
        current_time = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

        if video_manager and getattr(video_manager, "initialized", False):
            video_manager.update_frame(screen)
        else:
            screen.fill((25, 25, 35))
        screen.blit(overlay, (0, 0))

        player_count_selected = None
        btn_width = 120
        btn_height = 100
        total_width = (max_players - 1) * (btn_width + 20)
        start_x = screen.get_width() // 2 - total_width // 2

        for i in range(2, max_players + 1):
            btn_x = start_x + (i-2) * (btn_width + 20)
            btn_y = game_y + game_height // 2 - 50
            btn_rect = pygame.Rect(btn_x, btn_y, btn_width, btn_height)
            if btn_rect.collidepoint(mouse_pos):
                if hovered_player_button != i:
                    hovered_player_button = i
                    hover_start_time = current_time
                if current_time - hover_start_time >= 1.0:
                    selected_players = i
                    hovered_player_button = None
                    break
            else:
                if hovered_player_button == i:
                    hovered_player_button = None

        start_rect = pygame.Rect(screen.get_width() // 2 - 120, game_y + game_height // 2 + 70, 240, 80)
        if start_rect.collidepoint(mouse_pos):
            if hovered_button != "start":
                hovered_button = "start"
                hover_start_time = current_time
            if current_time - hover_start_time >= 1.0:
                game_completed = launch_game(screen, game["name"], selected_players, video_manager, hand_tracker=hand_tracker)
                hovered_button = None
                if game_completed is False:
                    return
        else:
            if hovered_button == "start":
                hovered_button = None

        font_large = pygame.font.SysFont("Arial", 48, bold=True)
        title = font_large.render(f"{game['name']} - Player Selection", True, (240, 240, 240))
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 50))

        pygame.draw.rect(screen, (30, 30, 45), (game_x, game_y, game_width, game_height), border_radius=15)
        pygame.draw.rect(screen, (60, 60, 90), (game_x, game_y, game_width, game_height), width=3, border_radius=15)

        draw_player_control_areas_preview(screen, selected_players, game_x, game_y, game_width, game_height, board_shape)

        font_medium = pygame.font.SysFont("Arial", 36)
        select_text = font_medium.render("Select Number of Players:", True, (240, 240, 240))
        screen.blit(select_text, (screen.get_width() // 2 - select_text.get_width() // 2, game_y + game_height // 2 - 120))

        player_colors = PLAYER_COLORS
        for i in range(2, max_players + 1):
            btn_x = start_x + (i-2) * (btn_width + 20)
            btn_y = game_y + game_height // 2 - 50
            is_selected = (i == selected_players)
            btn_color = player_colors[(i-1) % len(player_colors)] if is_selected else (100, 100, 120)
            btn_rect = draw_button(screen, btn_x, btn_y, btn_width, btn_height, str(i), False, btn_color, font_medium)
            if btn_rect.collidepoint(mouse_pos) and hovered_player_button == i:
                hover_time = current_time - hover_start_time
                draw_hover_timer(screen, mouse_pos, hover_time)

        start_hover = start_rect.collidepoint(mouse_pos)
        draw_button(screen, screen.get_width() // 2 - 120, game_y + game_height // 2 + 70, 240, 80, "START GAME", start_hover, font=font_medium)
        if start_hover and hovered_button == "start":
            hover_time = current_time - hover_start_time
            draw_hover_timer(screen, mouse_pos, hover_time)

        # Draw Exit button (bottom-right) — require long hover to return to game selection
        exit_w, exit_h = 160, 44
        exit_x = screen.get_width() - exit_w - 16
        exit_y = screen.get_height() - exit_h - 16
        is_exit_hover = pygame.Rect(exit_x, exit_y, exit_w, exit_h).collidepoint(mouse_pos)
        exit_rect = draw_button(screen, exit_x, exit_y, exit_w, exit_h, "EXIT", is_exit_hover, color=(160,40,40), font=font_medium)
        if exit_rect.collidepoint(mouse_pos):
            if exit_hover_start is None:
                exit_hover_start = current_time
            else:
                hover_time = current_time - exit_hover_start
                draw_hover_timer(screen, mouse_pos, hover_time, required_time=EXIT_HOVER_REQUIRED)
                if hover_time >= EXIT_HOVER_REQUIRED:
                    # return from player selection to game selection
                    return
        else:
            exit_hover_start = None

        # draw fingertip indicators last so they appear above all UI
        try:
            for tip in tips:
                pos = tip.get("screen")
                if pos:
                    pygame.draw.circle(screen, (0, 0, 0), pos, 14, 4)
                    pygame.draw.circle(screen, (60, 220, 80), pos, 8)
        except Exception:
            pass

        pygame.display.flip()
        clock = pygame.time.Clock()
        clock.tick(60)

# Make sure the function is available for import
if __name__ != "__main__":
    pass