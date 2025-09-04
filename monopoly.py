# Orchestrator: wire UI + logic modules and keep run loop
import pygame, time, random, math
from monopoly_logic import (
    initialize_players, new_shuffled_deck, draw_from_deck, handle_player_landing,
    RAILROAD_SPACES, UTILITY_SPACES
)
from monopoly_ui import draw_card_popup, draw_property_popup, draw_player_control_areas, draw_properties_panel
from ui_components import draw_hover_timer, draw_button
from game_utils import load_board_image, get_property_centers, get_player_positions
from constants import (
    COMMUNITY_CHEST_CARDS, CHANCE_CARDS,
    PROPERTIES, PROPERTY_SPACE_INDICES, RAILROADS, UTILITIES
)

def perform_dice_roll(screen, player, players, current_player_idx, player_position, positions,
                      video_manager, overlay, board_image, board_x, board_y,
                      game_x, game_y, game_width, game_height, num_players,
                      community_deck=None, chance_deck=None):
    """
    Dice-first animation:
    - Show large centered rolling dice for 2..4 seconds
    - Freeze on final values briefly
    - Then move the token step-by-step (with final dice still visible)
    Returns (success: bool, result: dict or None) to match caller expectations.
    """
    fps_clock = pygame.time.Clock()
    centers40 = get_property_centers(game_x + board_x, game_y + board_y, board_image.get_width(), board_image.get_height(), 40)

    # helper to draw two dice with pips; size adjustable
    def draw_dice_values(surf, d1, d2, anchor_x, anchor_y, size=140, gap=18):
        die1_rect = pygame.Rect(anchor_x, anchor_y, size, size)
        die2_rect = pygame.Rect(anchor_x + size + gap, anchor_y, size, size)
        pygame.draw.rect(surf, (240,240,240), die1_rect, border_radius=12)
        pygame.draw.rect(surf, (240,240,240), die2_rect, border_radius=12)
        pygame.draw.rect(surf, (10,10,10), die1_rect, 3, border_radius=12)
        pygame.draw.rect(surf, (10,10,10), die2_rect, 3, border_radius=12)
        def pip(cx, cy, r=max(6, size//18)):
            pygame.draw.circle(surf, (10,10,10), (int(cx), int(cy)), r)
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
        draw_pips(die1_rect, d1); draw_pips(die2_rect, d2)

    def draw_scene_skip(moving_idx=None, moving_pos_override=None, dice_vals=None, dice_offset=(0,0), dice_size=140):
        # draw full scene (board, tokens and player control areas) so action panels remain visible during animation
        if video_manager and getattr(video_manager, "initialized", False):
            try: video_manager.update_frame(screen)
            except Exception: screen.fill((25,25,35))
            screen.blit(overlay, (0,0))
        else:
            screen.fill((25,25,35))
        pygame.draw.rect(screen, (30,30,45), (game_x, game_y, game_width, game_height), border_radius=15)
        pygame.draw.rect(screen, (60,60,90), (game_x, game_y, game_width, game_height), width=3, border_radius=15)
        if board_image: screen.blit(board_image, (game_x + board_x, game_y + board_y))

        # draw player control areas so they don't disappear while moving
        try:
            draw_player_control_areas(screen, players, current_player_idx, game_x, game_y, game_width, game_height, "square", None)
        except Exception:
            pass

        # draw tokens (skip moving_idx)
        players_on_space = {}
        for pi, pl in enumerate(players):
            if moving_idx is not None and pi == moving_idx: continue
            bidx = pl.position % 40
            players_on_space.setdefault(bidx, []).append(pi)
        for bidx, plist in players_on_space.items():
            cx, cy = centers40[bidx]
            n = len(plist)
            if n <= 1:
                for pi in plist:
                    color = players[pi].color or (200,200,200)
                    pygame.draw.circle(screen, color, (int(cx), int(cy)), 12)
                    pygame.draw.circle(screen, (0,0,0), (int(cx), int(cy)), 12, 2)
            else:
                radius = 16
                for k, pi in enumerate(plist):
                    angle = 2*math.pi*k/n
                    px = int(cx + math.cos(angle)*radius); py = int(cy + math.sin(angle)*radius)
                    color = players[pi].color or (200,200,200)
                    pygame.draw.circle(screen, color, (px, py), 10); pygame.draw.circle(screen, (0,0,0), (px, py), 10, 2)
        if moving_idx is not None and moving_pos_override is not None:
            mx, my = moving_pos_override; color = players[moving_idx].color or (200,200,200)
            pygame.draw.circle(screen, color, (int(mx), int(my)), 12); pygame.draw.circle(screen, (0,0,0), (int(mx), int(my)), 12, 2)

        # draw dice values (if provided) so they're always visible during animation
        if dice_vals:
            try:
                d1, d2 = dice_vals
                size = dice_size
                gap = max(12, size//10)
                total_w = size*2 + gap
                anchor_x = screen.get_width()//2 - total_w//2 + dice_offset[0]
                anchor_y = screen.get_height()//2 - size//2 + dice_offset[1]
                draw_dice_values(screen, d1, d2, anchor_x, anchor_y, size=size, gap=gap)
            except Exception:
                pass

    # --- rolling phase (2..4s) with rapidly changing faces ---
    roll_duration = random.uniform(2.0, 4.0)
    t0 = time.time()
    while time.time() - t0 < roll_duration:
        rd1 = random.randint(1,6); rd2 = random.randint(1,6)
        # slight wobble while rolling
        wobble_x = int(math.sin((time.time()-t0)*12) * 8)
        wobble_y = int(math.cos((time.time()-t0)*10) * 6)
        draw_scene_skip(dice_vals=(rd1, rd2), dice_offset=(wobble_x, wobble_y), dice_size=160)
        pygame.display.flip()
        fps_clock.tick(30)

    # final dice
    d1 = random.randint(1,6); d2 = random.randint(1,6)

    # compute consecutive doubles and handle triple-doubles immediately:
    new_consec = getattr(player, "consecutive_doubles", 0) + (1 if d1 == d2 else 0)
    if d1 == d2 and new_consec >= 3:
        # Three doubles -> immediate jail (no movement, no $200 for passing GO)
        player.position = 10
        player.consecutive_doubles = 0
        player.has_rolled = True
        player.can_reroll = False
        # show final dice for a moment so user sees the triple-doubles result
        final_show_time = 0.6
        t1 = time.time()
        while time.time() - t1 < final_show_time:
            draw_scene_skip(dice_vals=(d1, d2), dice_offset=(0,0), dice_size=180)
            pygame.display.flip(); fps_clock.tick(30)
        return True, {"type":"jail","reason":"three_doubles"}

    # show final for a short moment so player sees outcome
    final_show_time = 0.6
    t1 = time.time()
    while time.time() - t1 < final_show_time:
        draw_scene_skip(dice_vals=(d1, d2), dice_offset=(0,0), dice_size=180)
        pygame.display.flip(); fps_clock.tick(30)

    total = d1 + d2

    # update consecutive doubles for non-triple case (keep for later logic)
    if d1 == d2:
        player.consecutive_doubles = new_consec
    else:
        player.consecutive_doubles = 0

    # now move the token step-by-step (preserve dice display during movement)
    per_tile = 0.12  # faster per-tile movement since dice already rolled
    for _ in range(total):
        start_idx = player.position; end_idx = (player.position + 1) % 40
        sx, sy = centers40[start_idx]; ex, ey = centers40[end_idx]
        t0 = time.time()
        while True:
            t = time.time() - t0
            if t >= per_tile: break
            p = t / per_tile
            ix = sx + (ex - sx) * p; iy = sy + (ey - sy) * p
            jump = math.sin(p * math.pi) * 12
            draw_scene_skip(moving_idx=current_player_idx, moving_pos_override=(ix, iy - jump), dice_vals=(d1, d2), dice_offset=(0,0), dice_size=160)
            pygame.display.flip(); fps_clock.tick(60)
        player.position = end_idx
        if player.position == 0:
            player.money += 200

    # handle doubles option and landing logic (same as before)
    # (consecutive_doubles already set above)
    success, result = handle_player_landing(player, players, dice_sum=total, community_deck=community_deck, chance_deck=chance_deck)
    if not success:
        return False, result

    player.can_reroll = (d1 == d2)
    player.has_rolled = True
    return True, result

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
    # state for buy-buttons inside the properties panel
    buy_hover_start = None
    hovered_buy_prop = None
    # exit-to-main-menu hover state
    exit_hover_start = None
    EXIT_HOVER_REQUIRED = 10.0  # seconds to hover to exit to main menu

    community_deck = new_shuffled_deck(COMMUNITY_CHEST_CARDS)
    chance_deck = new_shuffled_deck(CHANCE_CARDS)

    game_width = screen.get_width() - 600
    game_height = screen.get_height() - 300
    game_x = 300; game_y = 150

    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((25,25,35,180))

    board_image, board_x, board_y = load_board_image(game_width, game_height, "monopoly.jpg")

    running = True
    while running:
        current_player = players[current_player_idx]

        # compute board/player positions once per frame (fixes NameError when perform_dice_roll expects positions)
        try:
            positions = get_player_positions(len(players), "square")
        except Exception:
            positions = [(0,0)] * len(players)

        # Prefer smoothed tips from hand_tracker (fast background thread)
        tips = []
        if hand_tracker:
            try:
                tips = hand_tracker.get_tips()
            except Exception:
                tips = []

        # compute player_rects so we can assign tips to players
        try:
            player_rects, action_rects_map = draw_player_control_areas(screen, players, current_player_idx, game_x, game_y, game_width, game_height, "square", hover_info)
        except Exception:
            player_rects, action_rects_map = [], []

        # Map each detected tip to the nearest player rect center (allow simultaneous multi-player control)
        assigned_tip_for_player = {}  # player_idx -> (x,y, hand_idx)
        if tips and player_rects:
            # threshold relative to board size (projector coords)
            thresh = max(160, min(game_width, game_height) * 0.35)
            for pi, rect in enumerate(player_rects):
                ax, ay = rect.centerx, rect.centery
                best = None; best_d = None
                for t in tips:
                    tx, ty = t["screen"]; d = math.hypot(tx - ax, ty - ay)
                    if best is None or d < best_d:
                        best = t; best_d = d
                if best is not None and best_d <= thresh:
                    assigned_tip_for_player[pi] = (best["screen"][0], best["screen"][1], best["hand_idx"])

        # Determine active player's control point and active hand id (fallback to mouse)
        active_assignment = assigned_tip_for_player.get(current_player_idx)
        if active_assignment:
            mouse_pos = (active_assignment[0], active_assignment[1])
            active_hand_idx = active_assignment[2]
        else:
            mouse_pos = pygame.mouse.get_pos()
            active_hand_idx = None

        # Choose mouse_pos for hover logic (fallback per-player if no tip)
        # NOTE: we will use assigned_tip_for_player per-player below when checking each player's action rects.
        current_time = time.time()

        # --- render background & board (unchanged) ---
        if video_manager and getattr(video_manager, "initialized", False):
            try: video_manager.update_frame(screen)
            except Exception: screen.fill((25,25,35))
            screen.blit(overlay, (0,0))
        else:
            screen.fill((25,25,35))

        pygame.draw.rect(screen, (30,30,45), (game_x, game_y, game_width, game_height), border_radius=15)
        pygame.draw.rect(screen, (60,60,90), (game_x, game_y, game_width, game_height), width=3, border_radius=15)
        centers40 = None
        if board_image:
            screen.blit(board_image, (game_x + board_x, game_y + board_y))
            try:
                centers40 = get_property_centers(game_x + board_x, game_y + board_y, board_image.get_width(), board_image.get_height(), 40)
                players_on_space = {}
                for pi, pl in enumerate(players):
                    bi = pl.position % 40
                    players_on_space.setdefault(bi, []).append(pi)
                for bi, plist in players_on_space.items():
                    cx, cy = centers40[bi]; n = len(plist)
                    if n <= 1:
                        for pi in plist:
                            color = players[pi].color or (200,200,200)
                            pygame.draw.circle(screen, color, (int(cx), int(cy)), 12); pygame.draw.circle(screen, (0,0,0), (int(cx), int(cy)), 12, 2)
                    else:
                        r = 18
                        for k, pi in enumerate(plist):
                            ang = 2*math.pi*k/n; px = int(cx + math.cos(ang)*r); py = int(cy + math.sin(ang)*r)
                            color = players[pi].color or (200,200,200)
                            pygame.draw.circle(screen, color, (px, py), 10); pygame.draw.circle(screen, (0,0,0), (px, py), 10, 2)
            except Exception:
                centers40 = None

        # Re-draw control areas (we already called it to get rects above, but call again to ensure visuals)
        try:
            player_rects, action_rects_map = draw_player_control_areas(screen, players, current_player_idx, game_x, game_y, game_width, game_height, "square", hover_info)
        except Exception:
            player_rects, action_rects_map = [], []

        # If a popup was requested by landing logic, draw it here (before fingertip overlay)
        if show_property_popup and current_property:
            try:
                # determine player-side string for popup rotation/anchoring
                positions = get_player_positions(len(players), "square")
                player_side = positions[current_player_idx] if current_player_idx < len(positions) else "bottom"
                ptype = current_property.get("type")
                if ptype in ("chance", "community"):
                    # card-based popup
                    card = current_property.get("card")
                    draw_card_popup(screen, card, player_position=player_side)
                elif ptype in ("property", "railroad", "utility"):
                    prop = current_property.get("property")
                    owner = current_property.get("owner")
                    paid = current_property.get("paid")
                    draw_property_popup(screen, prop, owner=owner, paid=paid, player_position=player_side)
            except Exception:
                pass

        # draw fingertips: color the tip assigned to the active player with that player's color,
        # others desaturated / neutral
        try:
            for t in tips:
                pos = t.get("screen")
                hid = t.get("hand_idx")
                if not pos:
                    continue
                if hid is not None and hid == active_hand_idx:
                    c = current_player.color or (60,220,80)
                    outer = (0,0,0)
                    inner = c
                else:
                    outer = (30,30,30)
                    inner = (160,160,160)
                pygame.draw.circle(screen, outer, pos, 14, 4)
                pygame.draw.circle(screen, inner, pos, 8)
        except Exception:
            pass

        # --- existing hover/action logic below uses mouse_pos variable (unchanged), so only active player's tip triggers actions ---
        mouse_over_action = False
        for i, action_rects in enumerate(action_rects_map):
            for action, rect in action_rects.items():
                # If the active player's properties panel is open, disable Roll/Buy (and mortgage fallback)
                if show_properties and properties_player_idx is not None and i == current_player_idx and properties_player_idx == current_player_idx and action in (1, 2):
                    continue

                # Only allow hover handling for the active player (i == current_player_idx)
                if i != current_player_idx:
                    continue

                if rect.collidepoint(mouse_pos):
                    mouse_over_action = True
                    if hover_info is None or hover_info.get("player_idx")!=i or hover_info.get("action")!=action:
                        hover_info = {"player_idx": i, "action": action, "hover_time": 0}
                        hover_start_time = current_time; action_triggered = False
                    else:
                        hover_info["hover_time"] = current_time - hover_start_time
                        draw_hover_timer(screen, mouse_pos, hover_info["hover_time"])
                        if hover_info["hover_time"] >= 1.0 and not action_triggered:
                            action_triggered = True
                            # --- keep rest of action handling unchanged (roll/buy/properties) ---
                            if action == 1 and i == current_player_idx:
                                # roll / end-turn handling (same as before)
                                if not current_player.has_rolled:
                                    cont, res = perform_dice_roll(
                                        screen, current_player, players, current_player_idx,
                                        positions[current_player_idx], positions,
                                        video_manager, overlay, board_image, board_x, board_y,
                                        game_x, game_y, game_width, game_height, num_players,
                                        community_deck=community_deck, chance_deck=chance_deck
                                    )
                                    if not cont: return False
                                    if isinstance(res, dict):
                                        rtype = res.get("type")
                                        if rtype in ("property","railroad","utility","community","chance"):
                                            show_property_popup = True; current_property = res
                                    if isinstance(res, dict) and res.get("type") == "jail":
                                        current_player_idx = (current_player_idx + 1) % len(players)
                                else:
                                    if getattr(current_player, "can_reroll", False):
                                        cont, res = perform_dice_roll(
                                            screen, current_player, players, current_player_idx,
                                            positions[current_player_idx], positions,
                                            video_manager, overlay, board_image, board_x, board_y,
                                            game_x, game_y, game_width, game_height, num_players,
                                            community_deck=community_deck, chance_deck=chance_deck
                                        )
                                        if not cont: return False
                                        if isinstance(res, dict):
                                            rtype = res.get("type")
                                            if rtype in ("property","railroad","utility","community","chance"):
                                                show_property_popup = True; current_property = res
                                        current_player.can_reroll = False
                                        if isinstance(res, dict) and res.get("type") == "jail":
                                            current_player_idx = (current_player_idx + 1) % len(players)
                                    else:
                                        current_player.has_rolled = False; current_player.consecutive_doubles = 0
                                        current_player.can_reroll = False
                                        show_property_popup = False; current_property = None
                                        current_player_idx = (current_player_idx + 1) % len(players)
                                        hover_info = None; action_triggered = False
                            elif action == 2 and i == current_player_idx:
                                # buy/mortgage handling
                                # Determine what kind of space we're on and attempt purchase if available.
                                purchased = False
                                popup_result = None
                                # Property space
                                if current_player.position in PROPERTY_SPACE_INDICES:
                                    prop_idx = PROPERTY_SPACE_INDICES.index(current_player.position)
                                    # check ownership
                                    owned = any((p_prop.get("kind") == "property" and p_prop.get("index") == prop_idx)
                                                for pl in players for p_prop in pl.properties)
                                    price = PROPERTIES[prop_idx]["price"]
                                    if not owned and current_player.money >= price:
                                        if current_player.buy_property(prop_idx):
                                            purchased = True
                                            popup_result = {"type":"property", "property": PROPERTIES[prop_idx], "owner": current_player, "paid": price}
                                # Railroad space
                                elif current_player.position in RAILROAD_SPACES:
                                    ridx = RAILROAD_SPACES.index(current_player.position)
                                    owned = any((p_prop.get("kind") == "railroad" and p_prop.get("index") == ridx)
                                                for pl in players for p_prop in pl.properties)
                                    price = RAILROADS[ridx]["price"]
                                    if not owned and current_player.money >= price:
                                        if current_player.buy_railroad(ridx):
                                            purchased = True
                                            popup_result = {"type":"railroad", "property": RAILROADS[ridx], "owner": current_player, "paid": price}
                                # Utility space
                                elif current_player.position in UTILITY_SPACES:
                                    uidx = UTILITY_SPACES.index(current_player.position)
                                    owned = any((p_prop.get("kind") == "utility" and p_prop.get("index") == uidx)
                                                for pl in players for p_prop in pl.properties)
                                    price = UTILITIES[uidx]["price"]
                                    if not owned and current_player.money >= price:
                                        if current_player.buy_utility(uidx):
                                            purchased = True
                                            popup_result = {"type":"utility", "property": UTILITIES[uidx], "owner": current_player, "paid": price}

                                if purchased:
                                    # feedback to UI: show a small popup using existing popup function
                                    show_property_popup = True
                                    current_property = popup_result
                                else:
                                    # If cannot buy, fall back to mortgage UI or show message popup
                                    # Here we simply open the properties panel so player can mortgage/buy houses
                                    show_properties = True
                                    properties_player_idx = current_player_idx
                                    hover_info = None; action_triggered = False
                            elif action == 3 and i == current_player_idx:
                                # Open Properties panel for this player
                                show_properties = True
                                properties_player_idx = current_player_idx
                                hover_info = None; action_triggered = False
                    break
                if mouse_over_action: break

        if not mouse_over_action:
            hover_info = None; action_triggered = False

        # If properties panel is open, draw it and handle buy-house buttons (hover to trigger)
        if show_properties and properties_player_idx is not None:
            try:
                # anchor panel to the player's rect if available
                anchor = None
                if player_rects and properties_player_idx < len(player_rects):
                    anchor = player_rects[properties_player_idx]
                panel_rect, buy_buttons = draw_properties_panel(screen, players[properties_player_idx], anchor_rect=anchor, player_position=positions[properties_player_idx])
                # process buy-buttons via hover (1s)
                buy_hit = None
                for entry in buy_buttons:
                    rect = entry["rect"]; prop_idx = entry["property_index"]
                    if rect.collidepoint(mouse_pos):
                        buy_hit = entry
                        if hovered_buy_prop != prop_idx:
                            hovered_buy_prop = prop_idx
                            buy_hover_start = time.time()
                        else:
                            elapsed = time.time() - (buy_hover_start or time.time())
                            draw_hover_timer(screen, mouse_pos, elapsed)
                            if elapsed >= 1.0:
                                # attempt to buy house
                                bought = players[properties_player_idx].buy_house(prop_idx)
                                buy_hover_start = None; hovered_buy_prop = None
                                # refresh panel state visually
                                if bought:
                                    # keep panel open so user sees change
                                    pass
                                else:
                                    # not enough money or can't buy -> keep panel open
                                    pass
                        break
                if buy_hit is None:
                    buy_hover_start = None; hovered_buy_prop = None
            except Exception:
                pass

        # draw Exit Game button (bottom-right) and require long-hover to trigger
        exit_w, exit_h = 180, 48
        exit_x = screen.get_width() - exit_w - 16
        exit_y = screen.get_height() - exit_h - 16
        exit_rect = draw_button(screen, exit_x, exit_y, exit_w, exit_h, "EXIT GAME", False, color=(160,40,40))
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