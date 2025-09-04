import pygame
from constants import PROPERTIES, BOARD_ORIG_SIZE, CORNER_SIZE, EDGE_TILE_SIZE, PROPERTY_SPACE_INDICES

def get_player_positions(num_players, board_shape):
    """Get player positions based on count and board shape"""
    positions = []
    if board_shape == "square":
        if num_players == 1:
            positions = ["bottom"]
        elif num_players == 2:
            positions = ["top", "bottom"]
        elif num_players == 3:
            positions = ["top", "right", "bottom"]
        elif num_players == 4:
            positions = ["top", "right", "bottom", "left"]
        elif num_players == 5:
            positions = ["top", "top", "right", "bottom", "bottom"]
        elif num_players == 6:
            positions = ["top", "top", "right", "bottom", "bottom", "left"]
        elif num_players == 7:
            positions = ["top", "top", "top", "right", "bottom", "bottom", "bottom"]
        elif num_players == 8:
            positions = ["top", "top", "top", "right", "bottom", "bottom", "bottom", "left"]
    else:
        if num_players == 1:
            positions = ["bottom"]
        elif num_players == 2:
            positions = ["top", "bottom"]
        elif num_players == 3:
            positions = ["top", "bottom", "bottom"]
        elif num_players == 4:
            positions = ["top", "top", "bottom", "bottom"]
        elif num_players == 5:
            positions = ["top", "top", "bottom", "bottom", "right"]
        elif num_players == 6:
            positions = ["top", "top", "bottom", "bottom", "right", "left"]
        elif num_players == 7:
            positions = ["top", "top", "top", "bottom", "bottom", "bottom", "right"]
        elif num_players == 8:
            positions = ["top", "top", "top", "bottom", "bottom", "bottom", "right", "left"]
    return positions

def get_action_rectangles(player_idx, position, side, count_on_side, player_index_on_side, player_width, player_height):
    """Calculate rectangles for action buttons based on player position and side rectangle"""
    action_rects = {}
    if position in ["top", "bottom"]:
        action_width = (player_width - 40) // 3
        action_height = max(20, player_height - 30)
        for action in range(1, 4):
            action_x = side["x"] + player_index_on_side * player_width + 20 + (action - 1) * (action_width + 5)
            action_y = side["y"] + 15
            action_rects[action] = pygame.Rect(action_x, action_y, action_width, action_height)
    else:
        action_width = max(20, player_width - 30)
        action_height = (player_height - 40) // 3
        for action in range(1, 4):
            action_x = side["x"] + 15
            action_y = side["y"] + player_index_on_side * player_height + 20 + (action - 1) * (action_height + 5)
            action_rects[action] = pygame.Rect(action_x, action_y, action_width, action_height)
    return action_rects

def load_board_image(game_width, game_height, image_path="monopoly.jpg"):
    """Load and scale game board image while maintaining aspect ratio"""
    try:
        board_image = pygame.image.load(image_path)
        img_width, img_height = board_image.get_size()
        aspect_ratio = img_width / img_height
        if game_width / game_height > aspect_ratio:
            display_height = game_height
            display_width = int(display_height * aspect_ratio)
        else:
            display_width = game_width
            display_height = int(display_width / aspect_ratio)
        board_image = pygame.transform.scale(board_image, (display_width, display_height))
        board_x = (game_width - display_width) // 2
        board_y = (game_height - display_height) // 2
        return board_image, board_x, board_y
    except Exception:
        print("Could not load board image. Using default representation.")
        return None, 0, 0

def get_property_centers(board_x, board_y, display_width, display_height, count):
    """
    Compute precise centers for board spaces based on the original 2000x2000 artwork layout,
    scaled to the on-screen board image.

    - Produces 40 space centers ordered clockwise starting at index 0 = bottom-right corner (GO),
      then along bottom edge (right->left), left edge (bottom->top), top edge (left->right),
      and right edge (top->bottom).
    - If `count` equals len(PROPERTIES) and PROPERTY_SPACE_INDICES is defined, returns centers
      for those mapped property space indices (so each property appears at its canonical board space).
    - If count == 40 returns all 40 centers.
    - Otherwise falls back to an even-perimeter approximation for `count` items.
    """
    orig_w, orig_h = BOARD_ORIG_SIZE
    corner_w, corner_h = CORNER_SIZE
    tb_tile_w, tb_tile_h = EDGE_TILE_SIZE["top_bottom"]
    lr_tile_w, lr_tile_h = EDGE_TILE_SIZE["left_right"]

    # scale factor (board image is square because original is square)
    scale = display_width / orig_w if orig_w else 1.0

    # helper to scale original coords into screen coords
    def to_screen(orig_x, orig_y):
        sx = board_x + int(round(orig_x * scale))
        sy = board_y + int(round(orig_y * scale))
        return (sx, sy)

    centers = [None] * 40

    # Bottom-right corner (index 0)
    centers[0] = (orig_w - corner_w / 2.0, orig_h - corner_h / 2.0)
    # Bottom edge tiles (indices 1..9) moving right->left
    for i in range(1, 10):
        # i = 1 is immediately left of bottom-right corner
        x = orig_w - corner_w - tb_tile_w * (i - 0.5)
        y = orig_h - tb_tile_h / 2.0
        centers[i] = (x, y)
    # Bottom-left corner (index 10)
    centers[10] = (corner_w / 2.0, orig_h - corner_h / 2.0)
    # Left edge tiles (indices 11..19) moving bottom->top
    for j in range(1, 10):
        x = lr_tile_w / 2.0
        y = orig_h - corner_h - lr_tile_h * (j - 0.5)
        centers[10 + j] = (x, y)
    # Top-left corner (index 20)
    centers[20] = (corner_w / 2.0, corner_h / 2.0)
    # Top edge tiles (indices 21..29) moving left->right
    for k in range(1, 10):
        x = corner_w + tb_tile_w * (k - 0.5)
        y = tb_tile_h / 2.0
        centers[20 + k] = (x, y)
    # Top-right corner (index 30)
    centers[30] = (orig_w - corner_w / 2.0, corner_h / 2.0)
    # Right edge tiles (indices 31..39) moving top->bottom
    for m in range(1, 10):
        x = orig_w - lr_tile_w / 2.0
        y = corner_h + lr_tile_h * (m - 0.5)
        centers[30 + m] = (x, y)

    # convert to screen coords (apply scaling & board_x/board_y)
    screen_centers = [to_screen(cx, cy) for (cx, cy) in centers]

    # If the caller asked for standard properties count and mapping exists, return mapped centers
    if count == len(PROPERTIES) and isinstance(PROPERTY_SPACE_INDICES, (list, tuple)):
        mapped = []
        for idx in PROPERTY_SPACE_INDICES:
            if 0 <= idx < len(screen_centers):
                mapped.append(screen_centers[idx])
            else:
                # safety fallback to center of board if mapping is bad
                mapped.append((board_x + display_width // 2, board_y + display_height // 2))
        return mapped

    # If caller asked for full 40, return them
    if count == 40:
        return screen_centers

    # Fallback: evenly sample along the perimeter (keeps previous behaviour for other counts)
    left = board_x
    top = board_y
    right = board_x + display_width
    bottom = board_y + display_height
    perimeter = 2 * (display_width + display_height)
    approx = []
    for i in range(count):
        t = (i / count) * perimeter
        if t < display_width:
            x = right - t
            y = bottom
        elif t < display_width + display_height:
            t2 = t - display_width
            x = left
            y = bottom - t2
        elif t < 2 * display_width + display_height:
            t2 = t - (display_width + display_height)
            x = left + t2
            y = top
        else:
            t2 = t - (2 * display_width + display_height)
            x = right
            y = top + t2
        approx.append((int(x), int(y)))
    return approx