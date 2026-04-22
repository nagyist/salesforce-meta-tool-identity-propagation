#!/usr/bin/env python3
"""Generate animated diagram frames for the identity propagation flow."""
from PIL import Image, ImageDraw, ImageFont
import os, math

OUT = "/sessions/dazzling-sleepy-cori/diagram_frames"
os.makedirs(OUT, exist_ok=True)

W, H = 1920, 1080
FPS = 30

# Colors
BG = (74, 80, 184)       # #4a50b8 indigo
WHITE = (255, 255, 255)
WHITE_80 = (255, 255, 255, 204)
TEAMS_PURPLE = (91, 95, 199)
FOUNDRY_PURPLE = (119, 25, 170)
APIM_TEAL = (0, 130, 114)
SF_BLUE = (0, 161, 224)
DARK_BG = (55, 60, 140)
TOKEN_BLUE = (0, 120, 212)
TOKEN_GREEN = (16, 185, 129)
POLICY_BG = (45, 50, 120)
ARROW_COLOR = (180, 180, 255)
RETURN_GREEN = (16, 185, 129)

# Font
try:
    font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    font_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    font_xs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
except:
    font_lg = font_md = font_sm = font_xs = font_title = ImageFont.load_default()

# Box definitions - centered layout
BOX_W, BOX_H = 200, 120
BOX_Y = 200  # vertical center area
GAP = 100    # gap between boxes
TOTAL_W = 4 * BOX_W + 3 * GAP
START_X = (W - TOTAL_W) // 2

boxes = [
    {"name": "Teams",       "color": TEAMS_PURPLE,   "icon": "T",  "x": START_X},
    {"name": "AI Foundry",  "color": FOUNDRY_PURPLE, "icon": "AI", "x": START_X + BOX_W + GAP},
    {"name": "Azure APIM",  "color": APIM_TEAL,      "icon": "AP", "x": START_X + 2*(BOX_W + GAP)},
    {"name": "Salesforce",  "color": SF_BLUE,         "icon": "SF", "x": START_X + 3*(BOX_W + GAP)},
]

# Token definitions - appear between boxes
tokens = [
    {"text": "Azure AD Token", "from_idx": 0, "to_idx": 1, "color": TOKEN_BLUE},
    {"text": "Azure AD Token", "from_idx": 1, "to_idx": 2, "color": TOKEN_BLUE},
    {"text": "SF Access Token","from_idx": 2, "to_idx": 3, "color": TOKEN_GREEN},
]

# APIM policies
policies = [
    "1. Validate Azure AD JWT",
    "2. Resolve SF Username (from Azure AD oid)",
    "3. JWT Bearer OBO → Per-user SF Access Token",
]

def rounded_rect(draw, xy, radius, fill, outline=None):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)

def draw_arrow(draw, x1, y1, x2, y2, color=ARROW_COLOR, width=3):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    # arrowhead
    angle = math.atan2(y2-y1, x2-x1)
    size = 12
    draw.polygon([
        (x2, y2),
        (x2 - size*math.cos(angle-0.4), y2 - size*math.sin(angle-0.4)),
        (x2 - size*math.cos(angle+0.4), y2 - size*math.sin(angle+0.4)),
    ], fill=color)

def draw_token_pill(draw, cx, cy, text, color):
    tw = font_xs.getlength(text) + 24
    th = 28
    x0 = cx - tw//2
    y0 = cy - th//2
    rounded_rect(draw, (x0, y0, x0+tw, y0+th), radius=14, fill=color)
    draw.text((cx, cy), text, fill=WHITE, font=font_xs, anchor="mm")

def ease_out(t):
    return 1 - (1 - t)**3

def create_frame(frame_num):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    t = frame_num / FPS  # time in seconds

    # Title - always visible after 0.3s
    if t > 0.3:
        alpha = min(1.0, (t - 0.3) / 0.5)
        draw.text((W//2, 80), "Request Flow with Identity Propagation",
                  fill=WHITE, font=font_title, anchor="mm")

    # Phase 1: Boxes appear one by one (0.5s - 2.5s)
    for i, box in enumerate(boxes):
        appear_t = 0.5 + i * 0.5
        if t < appear_t:
            continue

        progress = min(1.0, (t - appear_t) / 0.4)
        progress = ease_out(progress)

        bx = box["x"]
        by = BOX_Y

        # Scale effect
        scale = progress
        cx = bx + BOX_W // 2
        cy = by + BOX_H // 2
        sw = int(BOX_W * scale)
        sh = int(BOX_H * scale)

        # White rounded box
        rounded_rect(draw,
                     (cx - sw//2, cy - sh//2, cx + sw//2, cy + sh//2),
                     radius=16, fill=WHITE)

        if progress > 0.5:
            # Icon circle
            icon_y = cy - 15
            draw.ellipse((cx-22, icon_y-22, cx+22, icon_y+22), fill=box["color"])
            draw.text((cx, icon_y), box["icon"], fill=WHITE, font=font_md, anchor="mm")
            # Label
            draw.text((cx, cy + 30), box["name"], fill=(36, 36, 36), font=font_md, anchor="mm")

        # Arrow to next box
        if i < 3 and t > appear_t + 0.3:
            arrow_progress = min(1.0, (t - appear_t - 0.3) / 0.3)
            next_x = boxes[i+1]["x"]
            ax1 = bx + BOX_W + 10
            ax2 = ax1 + (next_x - ax1 - 10) * ease_out(arrow_progress)
            ay = BOX_Y + BOX_H // 2
            draw_arrow(draw, ax1, ay, int(ax2), ay, color=ARROW_COLOR)

    # Phase 2: Tokens appear between boxes (3.0s - 5.5s)
    TOKEN_Y = BOX_Y + BOX_H + 40
    for i, token in enumerate(tokens):
        appear_t = 3.0 + i * 0.8
        if t < appear_t:
            continue

        progress = min(1.0, (t - appear_t) / 0.5)
        progress = ease_out(progress)

        from_box = boxes[token["from_idx"]]
        to_box = boxes[token["to_idx"]]
        cx = (from_box["x"] + BOX_W//2 + to_box["x"] + BOX_W//2) // 2
        cy = TOKEN_Y + i * 45

        if progress > 0:
            # Arrow line
            ax1 = from_box["x"] + BOX_W//2
            ax2 = to_box["x"] + BOX_W//2
            draw_arrow(draw, ax1, cy, ax2, cy, color=(*token["color"], int(200*progress)), width=2)
            # Token pill
            draw_token_pill(draw, cx, cy, token["text"], token["color"])

    # Phase 3: APIM Policy box (5.5s - 8.0s)
    POLICY_Y = TOKEN_Y + 160
    if t > 5.5:
        progress = min(1.0, (t - 5.5) / 0.5)
        progress = ease_out(progress)

        # Policy box under APIM
        apim_box = boxes[2]
        apim_cx = apim_box["x"] + BOX_W // 2
        pw = 520
        ph = 140
        px0 = apim_cx - pw//2
        py0 = POLICY_Y

        # Bracket line from APIM to policy box
        draw.line([(apim_cx, BOX_Y + BOX_H), (apim_cx, py0)],
                  fill=APIM_TEAL, width=2)

        # Policy box
        rounded_rect(draw, (px0, py0, px0 + pw, py0 + ph),
                     radius=12, fill=POLICY_BG, outline=APIM_TEAL)

        draw.text((apim_cx, py0 + 20), "APIM — Token Exchange Policy",
                  fill=WHITE, font=font_sm, anchor="mm")

        for j, policy in enumerate(policies):
            line_t = 6.0 + j * 0.5
            if t > line_t:
                line_progress = min(1.0, (t - line_t) / 0.3)
                draw.text((px0 + 20, py0 + 45 + j * 28), policy,
                          fill=(*WHITE[:3], int(255*line_progress)), font=font_xs)

    # Phase 4: Return arrow (8.0s - 10.0s)
    if t > 8.0:
        progress = min(1.0, (t - 8.0) / 0.8)
        progress = ease_out(progress)

        sf_box = boxes[3]
        teams_box = boxes[0]

        RETURN_Y = POLICY_Y + 170

        # Label
        draw.text((W//2, RETURN_Y - 25), "Salesforce Data returned to Teams",
                  fill=RETURN_GREEN, font=font_sm, anchor="mm")

        # Return arrow (right to left, below everything)
        rx1 = sf_box["x"] + BOX_W // 2
        rx2 = rx1 - (rx1 - teams_box["x"] - BOX_W//2) * progress
        draw_arrow(draw, rx1, RETURN_Y, int(rx2), RETURN_Y,
                   color=RETURN_GREEN, width=3)

        # Data pill on the arrow
        if progress > 0.3:
            pill_x = rx1 - (rx1 - teams_box["x"] - BOX_W//2) * min(1.0, (progress - 0.3) / 0.7)
            draw_token_pill(draw, int(pill_x), RETURN_Y, "Opportunities Data", RETURN_GREEN)

    return img

# Generate frames: 12 seconds at 30fps = 360 frames
TOTAL_FRAMES = 360
for i in range(TOTAL_FRAMES):
    img = create_frame(i)
    img.save(os.path.join(OUT, f"frame_{i:04d}.jpg"), quality=95)
    if i % 60 == 0:
        print(f"Frame {i}/{TOTAL_FRAMES}")

print(f"Done! {TOTAL_FRAMES} frames generated")
