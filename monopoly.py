# Orchestrator: wire UI + logic modules and keep run loop
import pygame, time, random, math
from monopoly_logic import (
    initialize_players, new_shuffled_deck, draw_from_deck, handle_player_landing,
    RAILROAD_SPACES, UTILITY_SPACES
)
from monopoly_ui import (
    draw_card_popup, draw_property_popup, draw_player_control_areas, draw_properties_panel
)
from ui_components import draw_hover_timer, draw_button
from game_utils import load_board_image, get_property_centers, get_player_positions
from constants import (
    COMMUNITY_CHEST_CARDS, CHANCE_CARDS,
    PROPERTIES, PROPERTY_SPACE_INDICES, RAILROADS, UTILITIES
)

# --- Helpers: keep logic identical but split into focused functions ---


def _draw_background_and_board(screen, video_manager, overlay, board_image, board_x, board_y,
                               game_x, game_y, game_width, game_height):
    """Draws the background video/solid fill and board container; returns whether board_image drawn."""
    if video_manager and getattr(video_manager, "initialized", False):
        try:
            video_manager.update_frame(screen)
        except Exception:
            screen.fill((25, 25, 35))
        screen.blit(overlay, (0, 0))
    else:
        screen.fill((25, 25, 35))
    pygame.draw.rect(screen, (30, 30, 45), (game_x, game_y, game_width, game_height), border_radius=15)
    pygame.draw.rect(screen, (60, 60, 90), (game_x, game_y, game_width, game_height), width=3, border_radius=15)
    if board_image:
        screen.blit(board_image, (game_x + board_x, game_y + board_y))
        return True
    return False


def _draw_tokens(screen, players, centers40, moving_idx=None, moving_pos_override=None):
    """Draw all tokens; skip moving_idx and draw it separately if moving_pos_override provided."""
    # gather players per space
    players_on_space = {}
    for pi, pl in enumerate(players):
        if moving_idx is not None and pi == moving_idx:
            continue
        bidx = pl.position % 40
        players_on_space.setdefault(bidx, []).append(pi)

    for bidx, plist in players_on_space.items():
        cx, cy = centers40[bidx]
        n = len(plist)
        if n <= 1:
            for pi in plist:
                color = players[pi].color or (200, 200, 200)
                pygame.draw.circle(screen, color, (int(cx), int(cy)), 12)
                pygame.draw.circle(screen, (0, 0, 0), (int(cx), int(cy)), 12, 2)
        else:
            radius = 16
            for k, pi in enumerate(plist):
                angle = 2 * math.pi * k / n
                px = int(cx + math.cos(angle) * radius)
                py = int(cy + math.sin(angle) * radius)
                color = players[pi].color or (200, 200, 200)
                pygame.draw.circle(screen, color, (px, py), 10)
                pygame.draw.circle(screen, (0, 0, 0), (px, py), 10, 2)

    if moving_idx is not None and moving_pos_override is not None:
        mx, my = moving_pos_override
        color = players[moving_idx].color or (200, 200, 200)
        pygame.draw.circle(screen, color, (int(mx), int(my)), 12)
        pygame.draw.circle(screen, (0, 0, 0), (int(mx), int(my)), 12, 2)


def _draw_dice(screen, dice_vals, dice_offset=(0, 0), dice_size=140):
    """Draw two dice centered on screen when dice_vals present."""
    if not dice_vals:
        return
    try:
        d1, d2 = dice_vals
        size = dice_size
        gap = max(12, size // 10)
        total_w = size * 2 + gap
        anchor_x = screen.get_width() // 2 - total_w // 2 + dice_offset[0]
        anchor_y = screen.get_height() // 2 - size // 2 + dice_offset[1]
        # draw two dice with pips as previously implemented
        die1_rect = pygame.Rect(anchor_x, anchor_y, size, size)
        die2_rect = pygame.Rect(anchor_x + size + gap, anchor_y, size, size)
        pygame.draw.rect(screen, (240, 240, 240), die1_rect, border_radius=12)
        pygame.draw.rect(screen, (240, 240, 240), die2_rect, border_radius=12)
        pygame.draw.rect(screen, (10, 10, 10), die1_rect, 3, border_radius=12)
        pygame.draw.rect(screen, (10, 10, 10), die2_rect, 3, border_radius=12)

        def pip(cx, cy, r=max(6, size // 18)):
            pygame.draw.circle(screen, (10, 10, 10), (int(cx), int(cy)), r)

        def draw_pips(rect, val):
            cx = rect.centerx; cy = rect.centery
            left = rect.left + rect.w * 0.28; right = rect.left + rect.w * 0.72
            top = rect.top + rect.h * 0.28; bottom = rect.top + rect.h * 0.72
            mid_y = cy; mid_x = cx
            if val == 1:
                pip(mid_x, mid_y)
            elif val == 2:
                pip(left, top); pip(right, bottom)
            elif val == 3:
                pip(left, top); pip(mid_x, mid_y); pip(right, bottom)
            elif val == 4:
                pip(left, top); pip(right, top); pip(left, bottom); pip(right, bottom)
            elif val == 5:
                pip(left, top); pip(right, top); pip(mid_x, mid_y); pip(left, bottom); pip(right, bottom)
            elif val == 6:
                pip(left, top); pip(right, top); pip(left, mid_y); pip(right, mid_y); pip(left, bottom); pip(right, bottom)

        draw_pips(die1_rect, d1)
        draw_pips(die2_rect, d2)
    except Exception:
        pass


def _assign_tips_to_players(tips, player_rects, game_width, game_height):
    """Return map player_idx -> (x,y,hand_idx) assigned based on nearest rect center + threshold."""
    assigned = {}
    if not tips or not player_rects:
        return assigned
    thresh = max(160, min(game_width, game_height) * 0.35)
    for pi, rect in enumerate(player_rects):
        ax, ay = rect.centerx, rect.centery
        best = None; best_d = None
        for t in tips:
            tx, ty = t["screen"]; d = math.hypot(tx - ax, ty - ay)
            if best is None or d < best_d:
                best = t; best_d = d
        if best is not None and best_d <= thresh:
            assigned[pi] = (best["screen"][0], best["screen"][1], best["hand_idx"])
    return assigned


def _draw_tips_overlay(screen, tips, active_hand_idx, current_player_color):
    """Draw fingertip markers identical to previous style."""
    try:
        for t in tips:
            pos = t.get("screen")
            hid = t.get("hand_idx")
            if not pos:
                continue
            if hid is not None and hid == active_hand_idx:
                c = current_player_color or (60, 220, 80)
                outer = (0, 0, 0)
                inner = c
            else:
                outer = (30, 30, 30)
                inner = (160, 160, 160)
            pygame.draw.circle(screen, outer, pos, 14, 4)
            pygame.draw.circle(screen, inner, pos, 8)
    except Exception:
        pass


# --- perform_dice_roll kept intact but uses helpers above for drawing pieces/dice ---
def perform_dice_roll(screen, player, players, current_player_idx, player_position, positions,
                      video_manager, overlay, board_image, board_x, board_y,
                      game_x, game_y, game_width, game_height, num_players,
                      community_deck=None, chance_deck=None):
    fps_clock = pygame.time.Clock()
    centers40 = get_property_centers(game_x + board_x, game_y + board_y,
                                     board_image.get_width(), board_image.get_height(), 40)

    def _draw_scene_full(moving_idx=None, moving_pos_override=None, dice_vals=None, dice_offset=(0, 0), dice_size=140):
        _draw_background_and_board(screen, video_manager, overlay, board_image, board_x, board_y, game_x, game_y, game_width, game_height)
        # draw control areas
        try:
            draw_player_control_areas(screen, players, current_player_idx, game_x, game_y, game_width, game_height, "square", None)
        except Exception:
            pass
        # draw tokens
        _draw_tokens(screen, players, centers40, moving_idx=moving_idx, moving_pos_override=moving_pos_override)
        # dice
        _draw_dice(screen, dice_vals, dice_offset, dice_size)

    # rolling animation (unchanged)
    roll_duration = random.uniform(2.0, 4.0)
    t0 = time.time()
    while time.time() - t0 < roll_duration:
        rd1 = random.randint(1, 6); rd2 = random.randint(1, 6)
        wobble_x = int(math.sin((time.time() - t0) * 12) * 8)
        wobble_y = int(math.cos((time.time() - t0) * 10) * 6)
        _draw_scene_full(dice_vals=(rd1, rd2), dice_offset=(wobble_x, wobble_y), dice_size=160)
        pygame.display.flip()
        fps_clock.tick(60)

    d1 = random.randint(1, 6); d2 = random.randint(1, 6)
    new_consec = getattr(player, "consecutive_doubles", 0) + (1 if d1 == d2 else 0)
    if d1 == d2 and new_consec >= 3:
        player.position = 10
        player.consecutive_doubles = 0
        player.has_rolled = True
        player.can_reroll = False
        final_show_time = 0.6
        t1 = time.time()
        while time.time() - t1 < final_show_time:
            _draw_scene_full(dice_vals=(d1, d2), dice_size=180)
            pygame.display.flip(); fps_clock.tick(60)
        return True, {"type": "jail", "reason": "three_doubles"}

    final_show_time = 0.6
    t1 = time.time()
    while time.time() - t1 < final_show_time:
        _draw_scene_full(dice_vals=(d1, d2), dice_size=180)
        pygame.display.flip(); fps_clock.tick(60)

    total = d1 + d2
    if d1 == d2:
        player.consecutive_doubles = new_consec
    else:
        player.consecutive_doubles = 0

    per_tile = 0.12
    for _ in range(total):
        start_idx = player.position; end_idx = (player.position + 1) % 40
        sx, sy = centers40[start_idx]; ex, ey = centers40[end_idx]
        t0 = time.time()
        while True:
            t = time.time() - t0
            if t >= per_tile:
                break
            p = t / per_tile
            ix = sx + (ex - sx) * p; iy = sy + (ey - sy) * p
            jump = math.sin(p * math.pi) * 12
            _draw_scene_full(moving_idx=current_player_idx, moving_pos_override=(ix, iy - jump), dice_vals=(d1, d2), dice_size=160)
            pygame.display.flip()
            fps_clock.tick(60)
        player.position = end_idx
        if player.position == 0:
            player.money += 200

    success, result = handle_player_landing(player, players, dice_sum=total, community_deck=community_deck, chance_deck=chance_deck)
    if not success:
        return False, result

    player.can_reroll = (d1 == d2)
    player.has_rolled = True
    return True, result


# --- run_monopoly_game refactored into clearer flow with helpers but same semantics ---
def run_monopoly_game(screen, num_players, video_manager=None, hand_tracker=None):
    clock = pygame.time.Clock()
    players = initialize_players(num_players)
    current_player_idx = 0
    show_properties = False
    properties_player_idx = None
    show_property_popup = False
    current_property = None
    hover_info = None
    hover_start_time = 0
    action_triggered = False
    panel_hover_start = None
    buy_hover_start = None
    hovered_buy_prop = None
    hover_states = {}
    exit_hover_start = None
    EXIT_HOVER_REQUIRED = 10.0

    community_deck = new_shuffled_deck(COMMUNITY_CHEST_CARDS)
    chance_deck = new_shuffled_deck(CHANCE_CARDS)

    game_width = screen.get_width() - 600
    game_height = screen.get_height() - 300
    game_x = 300; game_y = 150

    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((25, 25, 35, 180))

    board_image, board_x, board_y = load_board_image(game_width, game_height, "monopoly.jpg")

    # remote tip cache updated by pygame.USEREVENT+1 (posted by RemoteCameraClient)
    last_remote_tips = []

    # Inner helpers to keep cognitive complexity low in this main function:
    def _get_positions():
        try:
            return get_player_positions(len(players), "square")
        except Exception:
            return [(0, 0)] * len(players)
 
    def _fetch_tips():
        # prefer cached remote tips for lowest latency, otherwise call tracker API
        if last_remote_tips:
            return list(last_remote_tips)
        if not hand_tracker:
            return []
        try:
            return hand_tracker.get_tips()
        except Exception:
            return []
 
    def _compute_player_rects_and_assignments(tips, hover_info_local):
        try:
            player_rects_local, action_rects_map_local = draw_player_control_areas(
                screen, players, current_player_idx, game_x, game_y, game_width, game_height, "square", hover_info_local
            )
        except Exception:
            player_rects_local, action_rects_map_local = [], []
        assigned = _assign_tips_to_players(tips, player_rects_local, game_width, game_height)
        return player_rects_local, action_rects_map_local, assigned

    def _draw_main_scene(positions_local, centers40_local, tips_local, active_hand_idx_local):
        # background + board
        board_drawn = _draw_background_and_board(screen, video_manager, overlay, board_image, board_x, board_y,
                                                 game_x, game_y, game_width, game_height)
        centers40_out = None
        if board_drawn:
            try:
                centers40_out = get_property_centers(game_x + board_x, game_y + board_y,
                                                    board_image.get_width(), board_image.get_height(), 40)
            except Exception:
                centers40_out = None

        # draw control areas and tokens
        try:
            draw_player_control_areas(screen, players, current_player_idx, game_x, game_y, game_width, game_height, "square", hover_info)
        except Exception:
            pass
        if centers40_out:
            _draw_tokens(screen, players, centers40_out, moving_idx=None)

        # property popup (unchanged semantics)
        nonlocal show_property_popup, current_property
        if show_property_popup and current_property:
            try:
                pl_positions = get_player_positions(len(players), "square")
                player_side = pl_positions[current_player_idx] if current_player_idx < len(pl_positions) else "bottom"
                ptype = current_property.get("type")
                if ptype in ("chance", "community"):
                    draw_card_popup(screen, current_property.get("card"), player_position=player_side)
                elif ptype in ("property", "railroad", "utility"):
                    draw_property_popup(screen, current_property.get("property"), owner=current_property.get("owner"),
                                       paid=current_property.get("paid"), player_position=player_side)
            except Exception:
                pass

        # tips overlay
        _draw_tips_overlay(screen, tips_local, active_hand_idx_local, players[current_player_idx].color)

    def _process_action(action, i, rect, mouse_pos_local, positions_local):
        nonlocal hover_info, hover_start_time, action_triggered, current_player_idx, show_property_popup, current_property
        nonlocal panel_hover_start, buy_hover_start, hovered_buy_prop
        # maintain exact previous semantics for each action:
        if hover_info is None or hover_info.get("player_idx") != i or hover_info.get("action") != action:
            hover_info = {"player_idx": i, "action": action, "hover_time": 0}
            hover_start_time = time.time(); action_triggered = False
            return
        hover_info["hover_time"] = time.time() - hover_start_time
        draw_hover_timer(screen, mouse_pos_local, hover_info["hover_time"])
        if hover_info["hover_time"] >= 1.0 and not action_triggered:
            action_triggered = True
            if action == 1 and i == current_player_idx:
                # roll / end-turn handling (preserve original calls)
                if not players[current_player_idx].has_rolled:
                    cont, res = perform_dice_roll(
                        screen, players[current_player_idx], players, current_player_idx,
                        positions_local[current_player_idx], positions_local,
                        video_manager, overlay, board_image, board_x, board_y,
                        game_x, game_y, game_width, game_height, num_players,
                        community_deck=community_deck, chance_deck=chance_deck
                    )
                    if not cont: return "terminate"
                    if isinstance(res, dict):
                        rtype = res.get("type")
                        if rtype in ("property", "railroad", "utility", "community", "chance"):
                            show_property_popup = True; current_property = res
                    if isinstance(res, dict) and res.get("type") == "jail":
                        current_player_idx = (current_player_idx + 1) % len(players)
                else:
                    if getattr(players[current_player_idx], "can_reroll", False):
                        cont, res = perform_dice_roll(
                            screen, players[current_player_idx], players, current_player_idx,
                            positions_local[current_player_idx], positions_local,
                            video_manager, overlay, board_image, board_x, board_y,
                            game_x, game_y, game_width, game_height, num_players,
                            community_deck=community_deck, chance_deck=chance_deck
                        )
                        if not cont: return "terminate"
                        if isinstance(res, dict):
                            rtype = res.get("type")
                            if rtype in ("property", "railroad", "utility", "community", "chance"):
                                show_property_popup = True; current_property = res
                        players[current_player_idx].can_reroll = False
                        if isinstance(res, dict) and res.get("type") == "jail":
                            current_player_idx = (current_player_idx + 1) % len(players)
                    else:
                        players[current_player_idx].has_rolled = False; players[current_player_idx].consecutive_doubles = 0
                        players[current_player_idx].can_reroll = False
                        show_property_popup = False; current_property = None
                        current_player_idx = (current_player_idx + 1) % len(players)
                        hover_info = None; action_triggered = False
            elif action == 2 and i == current_player_idx:
                purchased = False
                popup_result = None
                if players[current_player_idx].position in PROPERTY_SPACE_INDICES:
                    # preserve original logic exactly
                    prop_idx = PROPERTY_SPACE_INDICES.index(current_current := players[current_player_idx].position if players[current_player_idx].position in PROPERTY_SPACE_INDICES else -1)
                    prop_idx = PROPERTY_SPACE_INDICES.index(players[current_player_idx].position)
                    owned = any((p_prop.get("kind") == "property" and p_prop.get("index") == prop_idx)
                                for pl in players for p_prop in pl.properties)
                    price = PROPERTIES[prop_idx]["price"]
                    if not owned and players[current_player_idx].money >= price:
                        if players[current_player_idx].buy_property(prop_idx):
                            purchased = True
                            popup_result = {"type": "property", "property": PROPERTIES[prop_idx], "owner": players[current_player_idx], "paid": price}
                elif players[current_player_idx].position in RAILROAD_SPACES:
                    ridx = RAILROAD_SPACES.index(players[current_player_idx].position)
                    owned = any((p_prop.get("kind") == "railroad" and p_prop.get("index") == ridx)
                                for pl in players for p_prop in pl.properties)
                    price = RAILROADS[ridx]["price"]
                    if not owned and players[current_player_idx].money >= price:
                        if players[current_player_idx].buy_railroad(ridx):
                            purchased = True
                            popup_result = {"type": "railroad", "property": RAILROADS[ridx], "owner": players[current_player_idx], "paid": price}
                elif players[current_player_idx].position in UTILITY_SPACES:
                    uidx = UTILITY_SPACES.index(players[current_player_idx].position)
                    owned = any((p_prop.get("kind") == "utility" and p_prop.get("index") == uidx)
                                for pl in players for p_prop in pl.properties)
                    price = UTILITIES[uidx]["price"]
                    if not owned and players[current_player_idx].money >= price:
                        if players[current_player_idx].buy_utility(uidx):
                            purchased = True
                            popup_result = {"type": "utility", "property": UTILITIES[uidx], "owner": players[current_player_idx], "paid": price}
                if purchased:
                    show_property_popup = True
                    current_property = popup_result
                else:
                    nonlocal_showprops = True
                    # show properties for this player
                    return "show_properties"
            elif action == 3 and i == current_player_idx:
                return "show_properties_only"
        return None

    def _handle_properties_panel(positions_local, assigned_local):
        nonlocal panel_hover_start, buy_hover_start, hovered_buy_prop, show_properties, properties_player_idx
        try:
            anchor = None
            if player_rects and properties_player_idx is not None and properties_player_idx < len(player_rects):
                anchor = player_rects[properties_player_idx]
            panel_rect, buy_buttons = draw_properties_panel(
                screen,
                players[properties_player_idx],
                anchor_rect=anchor,
                player_position=positions_local[properties_player_idx]
            )
            control_point = None
            assn = assigned_local.get(properties_player_idx)
            if assn:
                control_point = (assn[0], assn[1])
            elif properties_player_idx == current_player_idx:
                control_point = pygame.mouse.get_pos()

            if control_point:
                for entry in buy_buttons:
                    rect = entry["rect"]; prop_idx = entry["property_index"]
                    if rect.collidepoint(control_point):
                        if hovered_buy_prop != prop_idx:
                            hovered_buy_prop = prop_idx
                            buy_hover_start = time.time()
                        else:
                            elapsed = time.time() - (buy_hover_start or time.time())
                            draw_hover_timer(screen, control_point, elapsed)
                            if elapsed >= 1.0:
                                players[properties_player_idx].buy_house(prop_idx)
                                buy_hover_start = None; hovered_buy_prop = None
                        break
                else:
                    buy_hover_start = None; hovered_buy_prop = None

                if panel_rect.collidepoint(control_point):
                    if panel_hover_start is None:
                        panel_hover_start = time.time()
                    else:
                        ph_elapsed = time.time() - panel_hover_start
                        draw_hover_timer(screen, control_point, ph_elapsed)
                        if ph_elapsed >= 1.0:
                            return "close_properties"
                else:
                    panel_hover_start = None
            else:
                panel_hover_start = None
                buy_hover_start = None; hovered_buy_prop = None
        except Exception:
            panel_hover_start = None; buy_hover_start = None; hovered_buy_prop = None
        return None

    # Main run loop (now delegating to helpers)
    running = True
    while running:
        # process system / remote-tip events as early as possible (reduce latency)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
            elif event.type == pygame.USEREVENT + 1:
                try:
                    last_remote_tips = event.tips or []
                except Exception:
                    last_remote_tips = []
 
        current_player = players[current_player_idx]
        positions = _get_positions()
        tips = _fetch_tips()
        player_rects, action_rects_map, assigned = _compute_player_rects_and_assignments(tips, hover_info)

        # determine active assignment and mouse_pos
        active_assignment = assigned.get(current_player_idx)
        if active_assignment:
            mouse_pos = (active_assignment[0], active_assignment[1])
            active_hand_idx = active_assignment[2]
        else:
            # fallback: prefer the latest remote tip (real-time) as the pointer,
            # then hand_tracker.get_tips(), and finally the system mouse.
            if last_remote_tips:
                try:
                    first = last_remote_tips[0]
                    tp = first.get("screen")
                    mouse_pos = (int(tp[0]), int(tp[1])) if tp else pygame.mouse.get_pos()
                    active_hand_idx = first.get("hand_idx")
                except Exception:
                    mouse_pos = pygame.mouse.get_pos(); active_hand_idx = None
            else:
                mouse_pos = pygame.mouse.get_pos(); active_hand_idx = None

        current_time = time.time()

        # Draw scene
        _draw_main_scene(positions, None, tips, active_hand_idx)

        # Hover/action handling
        mouse_over_action = False
        for i, action_rects in enumerate(action_rects_map):
            for action, rect in action_rects.items():
                if show_properties and properties_player_idx is not None and i == current_player_idx and properties_player_idx == current_player_idx and action in (1, 2):
                    continue
                if i != current_player_idx:
                    continue
                if rect.collidepoint(mouse_pos):
                    mouse_over_action = True
                    res = _process_action(action, i, rect, mouse_pos, positions)
                    if res == "terminate":
                        return False
                    if res == "show_properties":
                        show_properties = True; properties_player_idx = current_player_idx
                        hover_info = None; action_triggered = False
                    if res == "show_properties_only":
                        show_properties = True; properties_player_idx = current_player_idx
                        hover_info = None; action_triggered = False
                    break
            if mouse_over_action:
                break

        if not mouse_over_action:
            hover_info = None; action_triggered = False

        # Properties panel handling
        if show_properties and properties_player_idx is not None:
            ph_res = _handle_properties_panel(positions, assigned)
            if ph_res == "close_properties":
                show_properties = False
                properties_player_idx = None
                panel_hover_start = None
                buy_hover_start = None
                hovered_buy_prop = None
                hover_states.clear()

        # Exit button handling
        exit_w, exit_h = 180, 48
        exit_x = screen.get_width() - exit_w - 16
        exit_y = screen.get_height() - exit_h - 16
        exit_rect = draw_button(screen, exit_x, exit_y, exit_w, exit_h, "EXIT GAME", False, color=(160, 40, 40))
        if exit_rect.collidepoint(mouse_pos):
            if exit_hover_start is None:
                exit_hover_start = current_time
            else:
                hover_time = current_time - exit_hover_start
                draw_hover_timer(screen, mouse_pos, hover_time, required_time=EXIT_HOVER_REQUIRED)
                if hover_time >= EXIT_HOVER_REQUIRED:
                    return False
        else:
            exit_hover_start = None

        pygame.display.flip()
        clock.tick(60)

    return True