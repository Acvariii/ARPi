import pygame
import time
import math
import pygame.gfxdraw
from constants import BUTTON_COLOR, BUTTON_HOVER, TEXT_COLOR, FONT_MEDIUM, FONT_ACTION

def draw_button(screen, x, y, width, height, text, hover=False, color=None, font=None, text_color=TEXT_COLOR):
    """Draw a styled button with hover effects and rounded corners"""
    if color is None:
        color = BUTTON_HOVER if hover else BUTTON_COLOR
    if font is None:
        font = FONT_MEDIUM

    border_color = (min(255, color[0] + 30), min(255, color[1] + 30), min(255, color[2] + 30))

    pygame.draw.rect(screen, color, (x, y, width, height), border_radius=10)
    pygame.draw.rect(screen, border_color, (x, y, width, height), width=2, border_radius=10)

    text_surface = font.render(text, True, text_color)
    screen.blit(text_surface, (x + width // 2 - text_surface.get_width() // 2,
                              y + height // 2 - text_surface.get_height() // 2))
    return pygame.Rect(x, y, width, height)

def draw_hover_timer(screen, mouse_pos, hover_time, required_time=1.0):
    """Draw a smooth circular progress indicator near mouse cursor for hover actions"""
    if hover_time <= 0:
        return
    # progress with clamping and eased interpolation for smooth motion
    raw = min(1.0, max(0.0, hover_time / required_time))
    # smoothstep easing (smooth start & end)
    progress = raw * raw * (3 - 2 * raw)

    cx, cy = mouse_pos[0] + 25, mouse_pos[1] + 25
    base_radius = 20
    bg_radius = base_radius
    inner_radius = base_radius - 4

    # background circle
    pygame.draw.circle(screen, (40, 40, 60), (cx, cy), bg_radius)
    pygame.draw.circle(screen, (80, 80, 100), (cx, cy), bg_radius, 2)

    # Higher-resolution sampling for a smooth sector
    try:
        if progress < 1.0:
            segments = 128  # increased resolution
            start_angle = -math.pi / 2
            end_angle = start_angle + 2 * math.pi * progress
            sample_count = max(4, int(segments * progress))
            pts = []
            # Center first so polygon forms a filled sector
            pts.append((cx, cy))
            for i in range(sample_count + 1):
                a = start_angle + (end_angle - start_angle) * (i / sample_count)
                x = cx + math.cos(a) * inner_radius
                y = cy + math.sin(a) * inner_radius
                pts.append((int(x), int(y)))
            # Use gfxdraw filled polygon (anti-aliased) when available for smoother edges
            try:
                pygame.gfxdraw.filled_polygon(screen, pts, (240, 240, 240))
                pygame.gfxdraw.aapolygon(screen, pts, (240, 240, 240))
            except Exception:
                pygame.draw.polygon(screen, (240, 240, 240), pts)
            # subtle inner ring to polish the look
            pygame.draw.circle(screen, (30,30,40), (cx, cy), inner_radius - 2, 1)
        else:
            # finished: pulsing ring for clarity (smooth pulse)
            pulse = 1.0 + 0.10 * math.sin(time.time() * 6.0)
            ring_r = int(base_radius * pulse)
            pygame.draw.circle(screen, (240, 240, 240), (cx, cy), ring_r, 3)
    except Exception:
        # safe fallback (keeps behavior if gfxdraw unavailable)
        end_angle = -math.pi/2 + 2*math.pi*progress
        pygame.draw.arc(screen, (240,240,240), (cx - inner_radius, cy - inner_radius, inner_radius*2, inner_radius*2),
                        -math.pi/2, end_angle, 3)

def draw_action_button(screen, rect, text, position, is_hovered=False):
    """Draw an action button with rotated text depending on position"""
    button_color = (100, 100, 120) if is_hovered else (60, 60, 80)
    pygame.draw.rect(screen, button_color, rect, border_radius=8)
    pygame.draw.rect(screen, (140, 140, 160) if is_hovered else (100, 100, 120),
                    rect, width=2, border_radius=8)
    angle = get_text_rotation_angle(position)
    draw_rotated_text(screen, text, rect.center, angle, FONT_ACTION, TEXT_COLOR)

def draw_rotated_text(screen, text, position, angle, font, color=TEXT_COLOR):
    """Draw rotated text centered at position"""
    text_surface = font.render(text, True, color)
    rotated_text = pygame.transform.rotate(text_surface, angle)
    screen.blit(rotated_text, (position[0] - rotated_text.get_width() // 2,
                               position[1] - rotated_text.get_height() // 2))

def get_text_rotation_angle(position):
    if position == "top":
        return 180
    if position == "right":
        return 90
    if position == "left":
        return 270
    return 0

# Helper for rainbow border if used
def hsv_to_rgb(h, s, v):
    if h == 1.0:
        h = 0.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i_mod = i % 6
    if i_mod == 0:
        return (int(v * 255), int(t * 255), int(p * 255))
    if i_mod == 1:
        return (int(q * 255), int(v * 255), int(p * 255))
    if i_mod == 2:
        return (int(p * 255), int(v * 255), int(t * 255))
    if i_mod == 3:
        return (int(p * 255), int(q * 255), int(v * 255))
    if i_mod == 4:
        return (int(t * 255), int(p * 255), int(v * 255))
    return (int(v * 255), int(p * 255), int(q * 255))

def draw_animated_rainbow_border(screen, rect, thickness=5, offset=0, speed=0.1):
    """Optional: animated rainbow border (keeps performance modest)"""
    current_time = time.time() * speed
    points = []
    step = max(2, min(rect.width, rect.height) // 40)
    for x in range(rect.left, rect.right + 1, step):
        points.append((x, rect.top))
    for y in range(rect.top, rect.bottom + 1, step):
        points.append((rect.right, y))
    for x in range(rect.right, rect.left - 1, -step):
        points.append((x, rect.bottom))
    for y in range(rect.bottom, rect.top - 1, -step):
        points.append((rect.left, y))
    if not points:
        return
    for i, (x, y) in enumerate(points):
        hue = ((i / len(points)) * 360 + current_time * 100 + offset) % 360
        color = hsv_to_rgb(hue / 360, 1.0, 1.0)
        pygame.draw.circle(screen, color, (x, y), max(1, thickness // 3))