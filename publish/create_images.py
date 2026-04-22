#!/usr/bin/env python3
"""Create LinkedIn thumbnail and article cover with identity flow diagram."""
from PIL import Image, ImageDraw, ImageFont
import math

# Fonts
font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
font_subtitle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
font_box = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
font_icon = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
font_token = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
font_policy = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
font_policy_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
font_badge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)

# Colors
WHITE = (255, 255, 255)
NEAR_WHITE = (248, 249, 252)
LIGHT_BG = (240, 242, 248)
TEXT_PRIMARY = (36, 36, 36)
TEXT_SECONDARY = (97, 97, 97)
TEAMS_PURPLE = (91, 95, 199)
FOUNDRY_PURPLE = (119, 25, 170)
APIM_TEAL = (0, 130, 114)
SF_BLUE = (0, 161, 224)
TOKEN_BLUE = (0, 120, 212)
TOKEN_GREEN = (16, 185, 129)
ACCENT_BAR = [(91,95,199), (0,120,212), (0,161,224), (119,25,170)]
POLICY_BG = (245, 246, 250)
BORDER_LIGHT = (224, 227, 234)
RETURN_GREEN = (16, 185, 129)
SHADOW = (0, 0, 0, 20)


def draw_rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_arrow(draw, x1, y1, x2, y2, color=(180,180,200), width=2):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    angle = math.atan2(y2-y1, x2-x1)
    size = 8
    draw.polygon([
        (x2, y2),
        (x2 - size*math.cos(angle-0.4), y2 - size*math.sin(angle-0.4)),
        (x2 - size*math.cos(angle+0.4), y2 - size*math.sin(angle+0.4)),
    ], fill=color)


def draw_token_pill(draw, cx, cy, text, color, font=font_token):
    tw = font.getlength(text) + 16
    th = 22
    x0 = cx - tw//2
    y0 = cy - th//2
    draw_rounded_rect(draw, (x0, y0, x0+tw, y0+th), radius=11, fill=color)
    draw.text((cx, cy), text, fill=WHITE, font=font, anchor="mm")


def draw_accent_bar(draw, x0, y0, w, h=4):
    seg = w // 4
    colors = ACCENT_BAR
    for i, c in enumerate(colors):
        draw.rectangle((x0 + i*seg, y0, x0 + (i+1)*seg, y0+h), fill=c)


def draw_diagram(draw, ox, oy, scale=1.0):
    """Draw the identity flow diagram at offset (ox, oy) with scale."""
    s = scale
    BOX_W, BOX_H = int(150*s), int(90*s)
    GAP = int(70*s)
    TOTAL_W = 4 * BOX_W + 3 * GAP
    START_X = ox
    BOX_Y = oy

    boxes = [
        {"name": "Teams",       "color": TEAMS_PURPLE,   "icon": "T",  "x": START_X},
        {"name": "AI Foundry",  "color": FOUNDRY_PURPLE, "icon": "AI", "x": START_X + BOX_W + GAP},
        {"name": "Azure APIM",  "color": APIM_TEAL,      "icon": "AP", "x": START_X + 2*(BOX_W + GAP)},
        {"name": "Salesforce",  "color": SF_BLUE,         "icon": "SF", "x": START_X + 3*(BOX_W + GAP)},
    ]

    # Draw boxes
    for i, box in enumerate(boxes):
        bx, by = box["x"], BOX_Y
        cx, cy = bx + BOX_W//2, by + BOX_H//2

        # Shadow
        draw_rounded_rect(draw, (bx+2, by+2, bx+BOX_W+2, by+BOX_H+2), radius=12, fill=(220,222,230))
        # Box
        draw_rounded_rect(draw, (bx, by, bx+BOX_W, by+BOX_H), radius=12, fill=WHITE, outline=BORDER_LIGHT)

        # Icon circle
        icon_y = cy - int(10*s)
        r = int(16*s)
        draw.ellipse((cx-r, icon_y-r, cx+r, icon_y+r), fill=box["color"])
        draw.text((cx, icon_y), box["icon"], fill=WHITE, font=font_icon, anchor="mm")
        # Label
        draw.text((cx, cy + int(18*s)), box["name"], fill=TEXT_PRIMARY, font=font_box, anchor="mm")

        # Arrow to next
        if i < 3:
            next_x = boxes[i+1]["x"]
            draw_arrow(draw, bx + BOX_W + 5, BOX_Y + BOX_H//2, next_x - 5, BOX_Y + BOX_H//2,
                       color=(180, 185, 210))

    # Tokens between boxes
    TOKEN_Y_START = BOX_Y + BOX_H + int(25*s)
    tokens = [
        {"text": "Azure AD Token", "from": 0, "to": 1, "color": TOKEN_BLUE},
        {"text": "Azure AD Token", "from": 1, "to": 2, "color": TOKEN_BLUE},
        {"text": "SF Access Token", "from": 2, "to": 3, "color": TOKEN_GREEN},
    ]
    for i, tok in enumerate(tokens):
        fb = boxes[tok["from"]]
        tb = boxes[tok["to"]]
        cy = TOKEN_Y_START + i * int(30*s)
        cx = (fb["x"] + BOX_W//2 + tb["x"] + BOX_W//2) // 2
        # Arrow line
        draw_arrow(draw, fb["x"]+BOX_W//2, cy, tb["x"]+BOX_W//2, cy, color=(*tok["color"], 150), width=1)
        draw_token_pill(draw, cx, cy, tok["text"], tok["color"], font=font_token)

    # APIM Policy box
    apim_cx = boxes[2]["x"] + BOX_W//2
    pw, ph = int(380*s), int(95*s)
    py0 = TOKEN_Y_START + 3 * int(30*s) + int(10*s)
    px0 = apim_cx - pw//2

    # Connector line
    draw.line([(apim_cx, BOX_Y + BOX_H), (apim_cx, py0)], fill=APIM_TEAL, width=1)

    # Policy box
    draw_rounded_rect(draw, (px0, py0, px0+pw, py0+ph), radius=8, fill=POLICY_BG, outline=APIM_TEAL, width=1)
    draw.text((apim_cx, py0 + int(14*s)), "APIM — Token Exchange Policy", fill=APIM_TEAL, font=font_policy_title, anchor="mm")
    policies = ["1. Validate Azure AD JWT", "2. Resolve SF Username (Azure AD oid)", "3. JWT Bearer OBO → SF Access Token"]
    for j, p in enumerate(policies):
        draw.text((px0 + int(12*s), py0 + int(28*s) + j*int(20*s)), p, fill=TEXT_SECONDARY, font=font_policy)

    # Return arrow
    RETURN_Y = py0 + ph + int(25*s)
    draw.text(((boxes[0]["x"] + BOX_W//2 + boxes[3]["x"] + BOX_W//2)//2, RETURN_Y - int(12*s)),
              "Salesforce Data → Teams", fill=RETURN_GREEN, font=font_small, anchor="mm")
    draw_arrow(draw, boxes[3]["x"]+BOX_W//2, RETURN_Y, boxes[0]["x"]+BOX_W//2, RETURN_Y,
               color=RETURN_GREEN, width=2)

    return TOTAL_W


# === THUMBNAIL 1920x1080 ===
W1, H1 = 1920, 1080
img1 = Image.new("RGB", (W1, H1), NEAR_WHITE)
draw1 = ImageDraw.Draw(img1)

# Accent bar
draw_accent_bar(draw1, 0, 0, W1, 5)

# Title area — push down for better vertical balance
draw1.text((W1//2, 100), "Microsoft Teams + Azure AI Foundry + Salesforce MCP",
           fill=TEXT_PRIMARY, font=font_title, anchor="mm")
draw1.text((W1//2, 145), "Identity Propagation — Per-user access, zero shared credentials",
           fill=TEXT_SECONDARY, font=font_subtitle, anchor="mm")

# Diagram centered vertically — scaled up to fill space
scale1 = 1.45
diagram_w = int((4*150 + 3*70) * scale1)
ox = (W1 - diagram_w) // 2
draw_diagram(draw1, ox, 250, scale=scale1)

# Microsoft + Salesforce badges at bottom
draw1.text((W1//2, H1 - 40), "MICROSOFT  +  SALESFORCE  •  OBO JWT Bearer  •  Azure APIM  •  MCP Server",
           fill=TEXT_SECONDARY, font=font_small, anchor="mm")

img1.save("/sessions/dazzling-sleepy-cori/mnt/salesforce-meta-tool-id-prop/linkedin-thumbnail.png", quality=95)
print("Thumbnail saved: 1920x1080")


# === ARTICLE COVER 1200x628 ===
W2, H2 = 1200, 628
img2 = Image.new("RGB", (W2, H2), NEAR_WHITE)
draw2 = ImageDraw.Draw(img2)

# Accent bar
draw_accent_bar(draw2, 0, 0, W2, 4)

# Title
font_cover_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
font_cover_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)

draw2.text((W2//2, 50), "Teams + AI Foundry + Salesforce MCP",
           fill=TEXT_PRIMARY, font=font_cover_title, anchor="mm")
draw2.text((W2//2, 82), "Identity Propagation with OBO JWT Bearer via Azure APIM",
           fill=TEXT_SECONDARY, font=font_cover_sub, anchor="mm")

# Diagram scaled to fit — push down slightly for balance
diagram_w_scaled = int((4*150 + 3*70) * 0.82)
ox2 = (W2 - diagram_w_scaled) // 2
draw_diagram(draw2, ox2, 130, scale=0.82)

# Footer
draw2.text((W2//2, H2 - 28), "Per-user access  •  Zero shared credentials  •  Full audit trail",
           fill=TEXT_SECONDARY, font=font_small, anchor="mm")

img2.save("/sessions/dazzling-sleepy-cori/mnt/salesforce-meta-tool-id-prop/linkedin-article-cover.png", quality=95)
print("Article cover saved: 1200x628")
