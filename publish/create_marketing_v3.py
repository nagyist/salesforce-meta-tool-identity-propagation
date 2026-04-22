from PIL import Image, ImageDraw, ImageFont
import math, os

def load_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

# ─── Colors ──────────────────────────────────────────────────────────
WHITE = (255, 255, 255)

def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def draw_gradient_bg(img):
    w, h = img.size
    top = (30, 15, 80)
    mid = (40, 30, 120)
    bot = (20, 50, 130)
    pixels = img.load()
    for y in range(h):
        t = y / h
        if t < 0.5:
            c = lerp_color(top, mid, t * 2)
        else:
            c = lerp_color(mid, bot, (t - 0.5) * 2)
        for x in range(w):
            pixels[x, y] = c

def draw_mesh_dots(od, w, h, alpha=10):
    for x in range(0, w, 50):
        for y in range(0, h, 50):
            od.ellipse([x-1, y-1, x+1, y+1], fill=(255, 255, 255, alpha))

# ─── Rounded square icon ────────────────────────────────────────────
def draw_rounded_rect(od, x0, y0, x1, y1, r, fill, outline=None, outline_w=1):
    od.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=outline, width=outline_w)

# ─── Icon drawing functions ──────────────────────────────────────────
def draw_teams_icon(od, cx, cy, size):
    """Purple rounded square with chat bubble icon"""
    s = size
    hs = s // 2
    # Background
    draw_rounded_rect(od, cx-hs, cy-hs, cx+hs, cy+hs, s//5, (88, 60, 190, 240))
    # Inner glow area
    draw_rounded_rect(od, cx-hs+4, cy-hs+4, cx+hs-4, cy+hs-4, s//6, (100, 75, 210, 200))
    
    # Chat bubble shape
    bw = int(s * 0.45)
    bh = int(s * 0.32)
    bx = cx - int(s * 0.05)
    by = cy - int(s * 0.08)
    od.rounded_rectangle([bx - bw//2, by - bh//2, bx + bw//2, by + bh//2], 
                         radius=6, fill=WHITE)
    # Tail
    tx = bx - bw//2 + 4
    ty = by + bh//2
    od.polygon([(tx, ty-2), (tx-6, ty+8), (tx+8, ty-2)], fill=WHITE)
    
    # Person silhouette on top-right
    px = cx + int(s * 0.18)
    py = cy - int(s * 0.22)
    pr = int(s * 0.08)
    od.ellipse([px-pr, py-pr, px+pr, py+pr], fill=WHITE)
    od.rounded_rectangle([px - int(pr*1.3), py + pr - 1, px + int(pr*1.3), py + int(pr*2.2)], 
                         radius=pr, fill=WHITE)

def draw_ai_foundry_icon(od, cx, cy, size):
    """Purple-magenta rounded square with molecular/network icon"""
    s = size
    hs = s // 2
    draw_rounded_rect(od, cx-hs, cy-hs, cx+hs, cy+hs, s//5, (140, 50, 160, 240))
    draw_rounded_rect(od, cx-hs+4, cy-hs+4, cx+hs-4, cy+hs-4, s//6, (160, 65, 180, 200))
    
    # Molecular/network nodes
    nr = int(s * 0.06)
    # Center node
    od.ellipse([cx-nr-1, cy-nr-1, cx+nr+1, cy+nr+1], fill=WHITE)
    # Surrounding nodes
    angles = [0, 72, 144, 216, 288]
    radius = int(s * 0.22)
    nodes = []
    for a in angles:
        rad = math.radians(a - 90)
        nx = cx + int(radius * math.cos(rad))
        ny = cy + int(radius * math.sin(rad))
        nodes.append((nx, ny))
        # Line from center
        od.line([(cx, cy), (nx, ny)], fill=(255, 255, 255, 200), width=2)
        od.ellipse([nx-nr, ny-nr, nx+nr, ny+nr], fill=WHITE)

def draw_apim_icon(od, cx, cy, size):
    """Teal/green rounded square with API list icon"""
    s = size
    hs = s // 2
    draw_rounded_rect(od, cx-hs, cy-hs, cx+hs, cy+hs, s//5, (0, 140, 120, 240))
    draw_rounded_rect(od, cx-hs+4, cy-hs+4, cx+hs-4, cy+hs-4, s//6, (0, 160, 140, 200))
    
    # Three horizontal lines (API/list)
    lw = int(s * 0.4)
    lh = 3
    gap = int(s * 0.12)
    for i in range(-1, 2):
        ly = cy + i * gap
        od.rounded_rectangle([cx - lw//2, ly - lh, cx + lw//2, ly + lh], radius=2, fill=WHITE)

def draw_salesforce_icon(od, cx, cy, size):
    """Blue rounded square with cloud icon"""
    s = size
    hs = s // 2
    draw_rounded_rect(od, cx-hs, cy-hs, cx+hs, cy+hs, s//5, (0, 140, 210, 240))
    draw_rounded_rect(od, cx-hs+4, cy-hs+4, cx+hs-4, cy+hs-4, s//6, (0, 160, 230, 200))
    
    # Cloud shape using overlapping circles
    cr = int(s * 0.13)
    cloud_y = cy - int(s * 0.02)
    # Base ellipse
    od.ellipse([cx - int(s*0.22), cloud_y - int(s*0.05), cx + int(s*0.22), cloud_y + int(s*0.15)], fill=WHITE)
    # Top bumps
    od.ellipse([cx - int(s*0.15) - cr, cloud_y - cr - 2, cx - int(s*0.15) + cr, cloud_y + cr - 2], fill=WHITE)
    od.ellipse([cx + int(s*0.05) - int(cr*1.2), cloud_y - int(cr*1.4) - 2, cx + int(s*0.05) + int(cr*1.2), cloud_y + int(cr*0.6) - 2], fill=WHITE)
    od.ellipse([cx - int(s*0.03) - cr, cloud_y - int(cr*0.8), cx - int(s*0.03) + cr, cloud_y + int(cr*1.2)], fill=WHITE)

def draw_servicenow_icon(od, cx, cy, size):
    """Green-yellow rounded square with plus icon"""
    s = size
    hs = s // 2
    draw_rounded_rect(od, cx-hs, cy-hs, cx+hs, cy+hs, s//5, (120, 170, 0, 240))
    draw_rounded_rect(od, cx-hs+4, cy-hs+4, cx+hs-4, cy+hs-4, s//6, (140, 190, 10, 200))
    
    # Plus/cross icon
    pw = int(s * 0.12)
    pl = int(s * 0.28)
    od.rounded_rectangle([cx - pw, cy - pl, cx + pw, cy + pl], radius=pw//2, fill=WHITE)
    od.rounded_rectangle([cx - pl, cy - pw, cx + pl, cy + pw], radius=pw//2, fill=WHITE)

def draw_anysaas_icon(od, cx, cy, size):
    """Gray rounded square with three dots"""
    s = size
    hs = s // 2
    draw_rounded_rect(od, cx-hs, cy-hs, cx+hs, cy+hs, s//5, (100, 100, 120, 200))
    draw_rounded_rect(od, cx-hs+4, cy-hs+4, cx+hs-4, cy+hs-4, s//6, (120, 120, 140, 160))
    
    # Three dots
    dr = int(s * 0.06)
    gap = int(s * 0.18)
    for i in range(-1, 2):
        dx = cx + i * gap
        od.ellipse([dx - dr, cy - dr, dx + dr, cy + dr], fill=WHITE)

# ─── Glass card (outer border around icon) ───────────────────────────
def draw_glass_card(od, cx, cy, size, padding=14):
    s = size + padding * 2
    hs = s // 2
    draw_rounded_rect(od, cx-hs, cy-hs, cx+hs, cy+hs, s//5,
                      fill=(255, 255, 255, 10), outline=(255, 255, 255, 30), outline_w=1)

# ─── Arrow with label ────────────────────────────────────────────────
def draw_arrow_h(od, x1, y, x2, label=None, font_size=14):
    """Horizontal arrow with optional label"""
    od.line([(x1, y), (x2 - 8, y)], fill=(255, 255, 255, 80), width=1)
    # Arrowhead
    od.polygon([(x2, y), (x2-10, y-5), (x2-10, y+5)], fill=(255, 255, 255, 80))
    if label:
        font = load_font(font_size, bold=False)
        od.text(((x1+x2)//2, y + 18), label, fill=(255, 255, 255, 100), font=font, anchor="mm")

def draw_arrow_v(od, x, y1, y2):
    """Short vertical arrow"""
    od.line([(x, y1), (x, y2 - 6)], fill=(255, 255, 255, 60), width=1)
    od.polygon([(x, y2), (x-4, y2-8), (x+4, y2-8)], fill=(255, 255, 255, 60))

# ─── MCP vertical label ─────────────────────────────────────────────
def draw_mcp_label(od, x, y, h, font_size=14):
    font = load_font(font_size, bold=True)
    text = "MCP"
    # Draw vertically by rotating... or just draw each letter
    for i, ch in enumerate(text):
        od.text((x, y + i * (font_size + 4)), ch, fill=(255, 255, 255, 60), font=font, anchor="mm")

# ─── Main image ──────────────────────────────────────────────────────
def create_image(W, H, is_thumbnail=True):
    base = Image.new("RGB", (W, H))
    draw_gradient_bg(base)
    
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    
    draw_mesh_dots(od, W, H, 8)
    
    # ─── Accent bar top (gradient purple→teal) ───────────────────
    for x in range(W):
        t = x / W
        c = lerp_color((140, 80, 255), (0, 220, 210), t)
        for yy in range(4):
            od.point((x, yy), fill=(*c, 200))
    
    if is_thumbnail:
        icon_size = 100
        
        # ─── TITLE ───────────────────────────────────────────────
        tag_font = load_font(15, bold=False)
        title_font = load_font(52, bold=True)
        
        # Part tag
        tag_text = "PART 2 — FROM THEORY TO PRODUCTION"
        tag_bbox = tag_font.getbbox(tag_text)
        tag_w = tag_bbox[2] - tag_bbox[0] + 40
        tag_h = 32
        tag_x = W // 2 - tag_w // 2
        tag_y = 55
        od.rounded_rectangle([tag_x, tag_y, tag_x + tag_w, tag_y + tag_h], 
                             radius=16, fill=(255, 255, 255, 12), outline=(255, 255, 255, 35))
        od.text((W // 2, tag_y + tag_h // 2), tag_text,
                fill=(255, 255, 255, 160), font=tag_font, anchor="mm")
        
        # Main title — two lines, with colored portion
        line1 = "In the Agent Era, SaaS Systems Risk"
        line2_a = "Becoming "
        line2_b = "Just Systems of Record"
        
        od.text((W // 2, 130), line1, fill=WHITE, font=title_font, anchor="mm")
        
        # Line 2: "Becoming" in white, "Just Systems of Record" in teal-green italic feel
        title_font_italic = load_font(52, bold=True)  # We don't have italic, use same
        bbox_a = title_font.getbbox(line2_a)
        w_a = bbox_a[2] - bbox_a[0]
        bbox_b = title_font.getbbox(line2_b)
        w_b = bbox_b[2] - bbox_b[0]
        total_w = w_a + w_b
        start_x = W // 2 - total_w // 2
        
        od.text((start_x, 195), line2_a, fill=WHITE, font=title_font, anchor="lm")
        od.text((start_x + w_a, 195), line2_b, fill=(120, 230, 180), font=title_font, anchor="lm")
        
        # ─── LAYOUT: Teams → AI Foundry → APIM, then APIM branches to SF/SN/Any ─
        # Left-to-right main flow
        teams_x = int(W * 0.18)
        ai_x = int(W * 0.40)
        apim_x = int(W * 0.62)
        
        main_y = int(H * 0.58)
        
        # Right side: vertical stack
        right_x = int(W * 0.82)
        sf_y = main_y - int(icon_size * 1.6)
        sn_y = main_y
        any_y = main_y + int(icon_size * 1.6)
        
        # Draw glass cards + icons
        draw_glass_card(od, teams_x, main_y, icon_size)
        draw_teams_icon(od, teams_x, main_y, icon_size)
        
        draw_glass_card(od, ai_x, main_y, icon_size)
        draw_ai_foundry_icon(od, ai_x, main_y, icon_size)
        
        draw_glass_card(od, apim_x, main_y, icon_size)
        draw_apim_icon(od, apim_x, main_y, icon_size)
        
        # Right side icons (smaller)
        rs = int(icon_size * 0.85)
        draw_glass_card(od, right_x, sf_y, rs)
        draw_salesforce_icon(od, right_x, sf_y, rs)
        
        draw_glass_card(od, right_x, sn_y, rs)
        draw_servicenow_icon(od, right_x, sn_y, rs)
        
        draw_glass_card(od, right_x, any_y, rs)
        draw_anysaas_icon(od, right_x, any_y, rs)
        
        # Labels
        label_font = load_font(18, bold=True)
        label_y_off = icon_size // 2 + 30
        od.text((teams_x, main_y + label_y_off), "Microsoft Teams", fill=(255, 255, 255, 200), font=label_font, anchor="mm")
        od.text((ai_x, main_y + label_y_off), "Azure AI Foundry", fill=(255, 255, 255, 200), font=label_font, anchor="mm")
        od.text((apim_x, main_y + label_y_off), "Azure APIM", fill=(255, 255, 255, 200), font=label_font, anchor="mm")
        
        rs_label_font = load_font(16, bold=True)
        rs_off = rs // 2 + 24
        od.text((right_x, sf_y + rs_off), "Salesforce", fill=(255, 255, 255, 180), font=rs_label_font, anchor="mm")
        od.text((right_x, sn_y + rs_off), "ServiceNow", fill=(255, 255, 255, 180), font=rs_label_font, anchor="mm")
        od.text((right_x, any_y + rs_off), "Any SaaS", fill=(255, 255, 255, 140), font=rs_label_font, anchor="mm")
        
        # ─── Arrows ─────────────────────────────────────────────
        arrow_off = icon_size // 2 + 18
        draw_arrow_h(od, teams_x + arrow_off, main_y, ai_x - arrow_off, "User token", 14)
        draw_arrow_h(od, ai_x + arrow_off, main_y, apim_x - arrow_off, "OBO exchange", 14)
        
        # APIM → right side (branching arrows)
        apim_right = apim_x + icon_size // 2 + 14
        rs_left = right_x - rs // 2 - 14
        
        # Arrow to SF (diagonal up-right)
        od.line([(apim_right, main_y - 10), (rs_left, sf_y)], fill=(255, 255, 255, 60), width=1)
        od.polygon([(rs_left, sf_y), (rs_left - 6, sf_y + 8), (rs_left - 10, sf_y - 2)], fill=(255, 255, 255, 60))
        
        # Arrow to SN (horizontal)
        od.line([(apim_right, main_y), (rs_left, sn_y)], fill=(255, 255, 255, 60), width=1)
        od.polygon([(rs_left, sn_y), (rs_left - 10, sn_y - 4), (rs_left - 10, sn_y + 4)], fill=(255, 255, 255, 60))
        
        # Arrow to Any (diagonal down-right)
        od.line([(apim_right, main_y + 10), (rs_left, any_y)], fill=(255, 255, 255, 60), width=1)
        od.polygon([(rs_left, any_y), (rs_left - 6, any_y - 8), (rs_left - 10, any_y + 2)], fill=(255, 255, 255, 60))
        
        # MCP label between APIM and right side
        mcp_x = (apim_right + rs_left) // 2
        draw_mcp_label(od, mcp_x, main_y - 25, 50, 16)
        
    else:
        # ─── ARTICLE COVER (1200x628) ───────────────────────────
        icon_size = 72
        
        tag_font = load_font(12, bold=False)
        title_font = load_font(36, bold=True)
        
        tag_text = "PART 2 — FROM THEORY TO PRODUCTION"
        tag_bbox = tag_font.getbbox(tag_text)
        tag_w = tag_bbox[2] - tag_bbox[0] + 30
        tag_h = 26
        tag_x = W // 2 - tag_w // 2
        tag_y = 30
        od.rounded_rectangle([tag_x, tag_y, tag_x + tag_w, tag_y + tag_h],
                             radius=13, fill=(255, 255, 255, 12), outline=(255, 255, 255, 30))
        od.text((W // 2, tag_y + tag_h // 2), tag_text,
                fill=(255, 255, 255, 150), font=tag_font, anchor="mm")
        
        line1 = "In the Agent Era, SaaS Systems Risk"
        line2_a = "Becoming "
        line2_b = "Just Systems of Record"
        
        od.text((W // 2, 90), line1, fill=WHITE, font=title_font, anchor="mm")
        
        bbox_a = title_font.getbbox(line2_a)
        w_a = bbox_a[2] - bbox_a[0]
        bbox_b = title_font.getbbox(line2_b)
        w_b = bbox_b[2] - bbox_b[0]
        total_w = w_a + w_b
        start_x = W // 2 - total_w // 2
        od.text((start_x, 138), line2_a, fill=WHITE, font=title_font, anchor="lm")
        od.text((start_x + w_a, 138), line2_b, fill=(120, 230, 180), font=title_font, anchor="lm")
        
        # Layout
        teams_x = int(W * 0.16)
        ai_x = int(W * 0.38)
        apim_x = int(W * 0.58)
        main_y = int(H * 0.58)
        
        right_x = int(W * 0.80)
        rs = int(icon_size * 0.78)
        sf_y = main_y - int(rs * 1.5)
        sn_y = main_y
        any_y = main_y + int(rs * 1.5)
        
        draw_glass_card(od, teams_x, main_y, icon_size)
        draw_teams_icon(od, teams_x, main_y, icon_size)
        draw_glass_card(od, ai_x, main_y, icon_size)
        draw_ai_foundry_icon(od, ai_x, main_y, icon_size)
        draw_glass_card(od, apim_x, main_y, icon_size)
        draw_apim_icon(od, apim_x, main_y, icon_size)
        
        draw_glass_card(od, right_x, sf_y, rs)
        draw_salesforce_icon(od, right_x, sf_y, rs)
        draw_glass_card(od, right_x, sn_y, rs)
        draw_servicenow_icon(od, right_x, sn_y, rs)
        draw_glass_card(od, right_x, any_y, rs)
        draw_anysaas_icon(od, right_x, any_y, rs)
        
        label_font = load_font(14, bold=True)
        lo = icon_size // 2 + 22
        od.text((teams_x, main_y + lo), "Microsoft Teams", fill=(255, 255, 255, 190), font=label_font, anchor="mm")
        od.text((ai_x, main_y + lo), "Azure AI Foundry", fill=(255, 255, 255, 190), font=label_font, anchor="mm")
        od.text((apim_x, main_y + lo), "Azure APIM", fill=(255, 255, 255, 190), font=label_font, anchor="mm")
        
        rs_lf = load_font(12, bold=True)
        rso = rs // 2 + 18
        od.text((right_x, sf_y + rso), "Salesforce", fill=(255, 255, 255, 170), font=rs_lf, anchor="mm")
        od.text((right_x, sn_y + rso), "ServiceNow", fill=(255, 255, 255, 170), font=rs_lf, anchor="mm")
        od.text((right_x, any_y + rso), "Any SaaS", fill=(255, 255, 255, 130), font=rs_lf, anchor="mm")
        
        arrow_off = icon_size // 2 + 18
        draw_arrow_h(od, teams_x + arrow_off, main_y, ai_x - arrow_off, "User token", 11)
        draw_arrow_h(od, ai_x + arrow_off, main_y, apim_x - arrow_off, "OBO exchange", 11)
        
        apim_right = apim_x + icon_size // 2 + 14
        rs_left = right_x - rs // 2 - 14
        od.line([(apim_right, main_y - 8), (rs_left, sf_y)], fill=(255, 255, 255, 50), width=1)
        od.line([(apim_right, main_y), (rs_left, sn_y)], fill=(255, 255, 255, 50), width=1)
        od.line([(apim_right, main_y + 8), (rs_left, any_y)], fill=(255, 255, 255, 50), width=1)
        
        mcp_x = (apim_right + rs_left) // 2
        draw_mcp_label(od, mcp_x, main_y - 18, 40, 13)
    
    result = Image.alpha_composite(base.convert("RGBA"), overlay)
    return result.convert("RGB")

out = "/sessions/dazzling-sleepy-cori/mnt/salesforce-meta-tool-id-prop"

thumb = create_image(1920, 1080, True)
thumb.save(f"{out}/linkedin-thumbnail.png", quality=95)
print("Thumbnail: 1920x1080")

cover = create_image(1200, 628, False)
cover.save(f"{out}/linkedin-article-cover.png", quality=95)
print("Cover: 1200x628")
