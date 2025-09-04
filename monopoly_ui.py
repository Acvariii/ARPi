# New module: rendering helpers (pygame)
import pygame
import math
from ui_components import draw_hover_timer, draw_action_button, draw_animated_rainbow_border, get_text_rotation_angle, draw_rotated_text
from game_utils import get_player_positions, get_action_rectangles, load_board_image, get_property_centers
from constants import PROPERTIES, PROPERTY_SPACE_INDICES, RAILROADS, UTILITIES, PLAYER_COLORS

RAILROAD_SPACES = [5, 15, 25, 35]
UTILITY_SPACES = [12, 28]
GO_SPACE = 0

def draw_card_popup(screen, card, player_position="bottom", anchor_rect=None):
    popup_w, popup_h = 420, 220
    s = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
    pygame.draw.rect(s, (40,40,60), (0,0,popup_w,popup_h), border_radius=10)
    pygame.draw.rect(s, (100,100,120), (0,0,popup_w,popup_h), 2, border_radius=10)
    font = pygame.font.SysFont("Arial", 16)
    text = card.get("text","")
    words = text.split(" ")
    lines=[]; line=""
    for w in words:
        if len(line + " " + w) > 48:
            lines.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line: lines.append(line)
    y = 12
    for ln in lines:
        r = font.render(ln, True, (220,220,220)); s.blit(r, (12, y)); y += r.get_height() + 6
    angle = get_text_rotation_angle(player_position)
    rotated = pygame.transform.rotate(s, angle)
    rect = rotated.get_rect()
    if anchor_rect:
        rect.centerx = anchor_rect.centerx; rect.bottom = anchor_rect.top - 8
    else:
        rect.center = (screen.get_width()//2, screen.get_height()//2)
    if rect.left < 8: rect.left = 8
    if rect.right > screen.get_width() - 8: rect.right = screen.get_width() - 8
    if rect.top < 8: rect.top = 8
    if rect.bottom > screen.get_height() - 8: rect.bottom = screen.get_height() - 8
    screen.blit(rotated, rect.topleft)
    return rect

def draw_property_popup(screen, property_data, owner=None, paid=None, anchor_rect=None, player_position="bottom"):
    popup_w, popup_h = 360, 220
    popup_surface = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
    pygame.draw.rect(popup_surface, (50,50,70), (0,0,popup_w,popup_h), border_radius=12)
    pygame.draw.rect(popup_surface, (100,100,120), (0,0,popup_w,popup_h), 2, border_radius=12)
    inner_w = popup_w - 40
    prop_card_h = 80
    prop_card_x = 20; prop_card_y = 16
    if property_data:
        prop_color = property_data.get("color") if isinstance(property_data, dict) else None
        if not prop_color:
            name = property_data.get("name","").lower()
            if "rail" in name:
                prop_color = (120,120,120)
            elif "electric" in name or "water" in name:
                prop_color = (100,140,220)
            else:
                prop_color = (180,180,180)
        pygame.draw.rect(popup_surface, prop_color, (prop_card_x, prop_card_y, inner_w, prop_card_h), border_radius=6)
        pygame.draw.rect(popup_surface, (0,0,0), (prop_card_x, prop_card_y, inner_w, prop_card_h), 2, border_radius=6)
        font = pygame.font.SysFont("Arial", 18)
        name = property_data.get("name", "Unknown")
        name_text = font.render(name, True, (0,0,0))
        popup_surface.blit(name_text, (prop_card_x + inner_w//2 - name_text.get_width()//2, prop_card_y + 8))
        font_small = pygame.font.SysFont("Arial", 14)
        price_val = property_data.get("price", 0)
        price_text = font_small.render(f"Price: ${price_val}", True, (0,0,0))
        popup_surface.blit(price_text, (prop_card_x + 12, prop_card_y + 44))
        if "rents" in property_data and property_data["rents"]:
            rent_display = property_data["rents"][0]
            rent_text = font_small.render(f"Rent: ${rent_display}", True, (0,0,0))
            popup_surface.blit(rent_text, (prop_card_x + inner_w - rent_text.get_width() - 12, prop_card_y + 44))
        elif "rent_steps" in property_data:
            rent_text = font_small.render(f"Rent: ${property_data['rent_steps'][0]}", True, (0,0,0))
            popup_surface.blit(rent_text, (prop_card_x + inner_w - rent_text.get_width() - 12, prop_card_y + 44))
        else:
            if "electric" in property_data.get("name","").lower() or "water" in property_data.get("name","").lower():
                rent_text = font_small.render("Rent: 4x or 10x dice", True, (0,0,0))
                popup_surface.blit(rent_text, (prop_card_x + inner_w - rent_text.get_width() - 12, prop_card_y + 44))
    else:
        font = pygame.font.SysFont("Arial", 16)
        msg = font.render("No property info", True, (220,220,220))
        popup_surface.blit(msg, (popup_w//2 - msg.get_width()//2, popup_h//2 - msg.get_height()//2))
    font_small = pygame.font.SysFont("Arial", 14)
    if owner:
        owner_text = font_small.render(f"Owner: {owner.name}", True, (220,220,220)); popup_surface.blit(owner_text, (12, popup_h - 56))
        if paid is not None:
            paid_text = font_small.render(f"Paid: ${paid}", True, (220,220,220)); popup_surface.blit(paid_text, (12, popup_h - 36))
    else:
        buy_text = font_small.render("Hover 'Buy' to purchase", True, (200,200,200)); popup_surface.blit(buy_text, (12, popup_h - 36))
    angle = get_text_rotation_angle(player_position)
    rotated = pygame.transform.rotate(popup_surface, angle)
    rect = rotated.get_rect()
    if anchor_rect:
        rect.centerx = anchor_rect.centerx
        rect.top = anchor_rect.bottom + 8
    else:
        rect.center = (screen.get_width()//2, screen.get_height()//2)
    if rect.left < 8: rect.left = 8
    if rect.right > screen.get_width() - 8: rect.right = screen.get_width() - 8
    if rect.top < 8: rect.top = 8
    if rect.bottom > screen.get_height() - 8: rect.bottom = screen.get_height() - 8
    screen.blit(rotated, rect.topleft)
    return rect

def draw_properties_panel(screen, player, anchor_rect=None, player_position="bottom"):
    panel_w, panel_h = 320, 220
    panel_surface = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(panel_surface, (40,40,60), (0,0,panel_w,panel_h), border_radius=8)
    pygame.draw.rect(panel_surface, (100,100,100), (0,0,panel_w,panel_h), 2, border_radius=8)
    font_small = pygame.font.SysFont("Arial", 14)
    title = font_small.render(f"{player.name}'s Properties", True, player.color)
    panel_surface.blit(title, (10,8))
    money_text = font_small.render(f"Money: ${player.money}", True, (200,200,200))
    panel_surface.blit(money_text, (10,30))
    buy_buttons_local = []
    y_start = 58
    for idx, prop in enumerate(player.properties):
        y = y_start + idx * 28
        # Determine colour: use property's defined colour for normal properties, use white for railroads/utilities
        prop_index = prop.get("index")
        if prop.get("kind") == "property" and isinstance(prop_index, int) and 0 <= prop_index < len(PROPERTIES):
            text_color = PROPERTIES[prop_index].get("color", (220,220,220))
        else:
            text_color = (255,255,255)
        prop_text = font_small.render(f"{prop['name']} (${prop.get('price',0)})", True, text_color)
        panel_surface.blit(prop_text, (10, y))
        prop_index = prop["index"]
        price_per_house = prop.get("price_per_house", 0)
        houses = prop.get("houses", 0)
        if prop.get("kind") == "property" and player.has_monopoly(prop_index) and houses < 5 and player.money >= price_per_house:
            btn_w, btn_h = 80, 20
            btn_x = panel_w - btn_w - 12; btn_y = y + 2
            pygame.draw.rect(panel_surface, (60,120,60), (btn_x, btn_y, btn_w, btn_h), border_radius=6)
            pygame.draw.rect(panel_surface, (90,160,90), (btn_x, btn_y, btn_w, btn_h), 2, border_radius=6)
            buy_text = pygame.font.SysFont("Arial", 12).render("Buy House", True, (240,240,240))
            panel_surface.blit(buy_text, (btn_x + btn_w//2 - buy_text.get_width()//2, btn_y + btn_h//2 - buy_text.get_height()//2))
            buy_buttons_local.append({"rect": pygame.Rect(btn_x, btn_y, btn_w, btn_h), "property_index": prop_index})
    angle = get_text_rotation_angle(player_position)
    rotated = pygame.transform.rotate(panel_surface, angle)
    rotated_rect = rotated.get_rect()
    if anchor_rect:
        if player_position == "bottom":
            centerx = anchor_rect.centerx; centery = anchor_rect.bottom + panel_h//2 + 8
        elif player_position == "top":
            centerx = anchor_rect.centerx; centery = anchor_rect.top - panel_h//2 - 8
        elif player_position == "right":
            centerx = anchor_rect.right + panel_w//2 + 8; centery = anchor_rect.centery
        else:
            centerx = anchor_rect.left - panel_w//2 - 8; centery = anchor_rect.centery
    else:
        centerx = screen.get_width()//2; centery = screen.get_height()//2
    rotated_rect.center = (centerx, centery)
    buy_buttons_screen = []
    panel_cx, panel_cy = panel_w/2, panel_h/2
    rad = math.radians(angle); cos_a, sin_a = math.cos(rad), math.sin(rad)
    for entry in buy_buttons_local:
        local_r = entry["rect"]
        local_cx = local_r.x + local_r.w/2; local_cy = local_r.y + local_r.h/2
        vx, vy = local_cx - panel_cx, local_cy - panel_cy
        rx = vx * cos_a - vy * sin_a; ry = vx * sin_a + vy * cos_a
        screen_cx = rotated_rect.centerx + rx; screen_cy = rotated_rect.centery + ry
        screen_rect = pygame.Rect(int(screen_cx - local_r.w/2), int(screen_cy - local_r.h/2), int(local_r.w), int(local_r.h))
        buy_buttons_screen.append({"rect": screen_rect, "property_index": entry["property_index"]})
    if rotated_rect.left < 8: rotated_rect.left = 8
    if rotated_rect.right > screen.get_width() - 8: rotated_rect.right = screen.get_width() - 8
    if rotated_rect.top < 8: rotated_rect.top = 8
    if rotated_rect.bottom > screen.get_height() - 8: rotated_rect.bottom = screen.get_height() - 8
    screen.blit(rotated, rotated_rect.topleft)
    return rotated_rect, buy_buttons_screen

def draw_player_control_areas(screen, players, current_player_idx, game_x, game_y, game_width, game_height, board_shape, hover_info):
    positions = get_player_positions(len(players), board_shape)
    sides = {
        "top": {"x": game_x, "y": 0, "width": game_width, "height": game_y},
        "right": {"x": game_x + game_width, "y": game_y, "width": screen.get_width() - (game_x + game_width), "height": game_height},
        "bottom": {"x": game_x, "y": game_y + game_height, "width": game_width, "height": screen.get_height() - (game_y + game_height)},
        "left": {"x": 0, "y": game_y, "width": game_x, "height": game_height}
    }
    side_counts = {"top":0,"right":0,"bottom":0,"left":0}
    for pos in positions: side_counts[pos] += 1
    player_rects = []; action_rects_map = []
    for i, position in enumerate(positions):
        player = players[i]
        player.color = player.color or (100,100,120)
        side = sides[position]
        count_on_side = side_counts[position]
        idx_on_side = positions[:i+1].count(position) - 1
        if position in ("top","bottom"):
            player_w = side["width"] // max(1, count_on_side); player_h = side["height"]
            px = side["x"] + idx_on_side * player_w; py = side["y"]
        else:
            player_w = side["width"]; player_h = side["height"] // max(1, count_on_side)
            px = side["x"]; py = side["y"] + idx_on_side * player_h
        rect = pygame.Rect(px, py, player_w, player_h)
        player_rects.append(rect)
        pygame.draw.rect(screen, player.color, rect, border_radius=6)
        if i == current_player_idx:
            draw_animated_rainbow_border(screen, rect, thickness=4, offset=i*30, speed=0.15)
        else:
            pygame.draw.rect(screen, (min(255,player.color[0]+40),min(255,player.color[1]+40),min(255,player.color[2]+40)), rect, width=3, border_radius=6)
        action_rects = get_action_rectangles(i, position, side, count_on_side, idx_on_side, player_w, player_h)
        action_rects_map.append(action_rects)
        for action, r in action_rects.items():
            if action == 1:
                # Show "Roll Dice" if player hasn't rolled OR if they have a reroll available (doubles)
                if not player.has_rolled or getattr(player, "can_reroll", False):
                    text = "Roll Dice"
                else:
                    text = "End Turn"
            elif action == 2:
                can_buy = False
                if player.has_rolled and i == current_player_idx:
                    if player.position in PROPERTY_SPACE_INDICES:
                        prop_idx = PROPERTY_SPACE_INDICES.index(player.position)
                        is_owned = any(p_owned.get("kind")=="property" and p_owned["index"]==prop_idx for pl in players for p_owned in pl.properties)
                        if (not is_owned) and player.money >= PROPERTIES[prop_idx]["price"]:
                            can_buy = True
                    elif player.position in RAILROAD_SPACES:
                        ridx = RAILROAD_SPACES.index(player.position)
                        is_owned = any(p_owned.get("kind")=="railroad" and p_owned["index"]==ridx for pl in players for p_owned in pl.properties)
                        if (not is_owned) and player.money >= RAILROADS[ridx]["price"]:
                            can_buy = True
                    elif player.position in UTILITY_SPACES:
                        uidx = UTILITY_SPACES.index(player.position)
                        is_owned = any(p_owned.get("kind")=="utility" and p_owned["index"]==uidx for pl in players for p_owned in pl.properties)
                        if (not is_owned) and player.money >= UTILITIES[uidx]["price"]:
                            can_buy = True
                text = "Buy" if can_buy else "Mortgage"
            else:
                text = "Properties"
            hovered = (hover_info and hover_info.get("player_idx")==i and hover_info.get("action")==action)
            draw_action_button(screen, r, text, position, hovered)
    return player_rects, action_rects_map