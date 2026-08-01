# make_icon.py — sadece uçak
import math, struct, io
from PIL import Image, ImageDraw

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def rounded_rect_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask

def make_frame(size):
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s    = size / 256
    cx   = cy = size / 2

    # Gradyan arka plan: mor → koyu mor
    for y in range(size):
        c = lerp_color((79, 70, 229), (109, 40, 217), y / size)
        draw.rectangle([(0, y), (size, y + 1)], fill=(*c, 255))
    img.putalpha(rounded_rect_mask(size, max(4, int(size * 0.22))))
    draw = ImageDraw.Draw(img)

    # Hafif iç parlaklık (üst)
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    gd.ellipse([cx - size*0.55, cy - size*0.85,
                cx + size*0.55, cy + size*0.15],
               fill=(255, 255, 255, 18))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    # Uçak — 45° sağ-yukarı bakıyor
    angle   = math.radians(-42)
    pw      = 95 * s    # uçak yarı uzunluğu
    wing_w  = 70 * s    # kanat açıklığı
    wing_h  = 22 * s
    tail_w  = 36 * s
    tail_h  = 14 * s
    body_h  = 13 * s

    def rot(bx, by):
        c, sv = math.cos(angle), math.sin(angle)
        return (cx + bx*c - by*sv, cy + bx*sv + by*c)

    # Gölge (hafif offset)
    shadow_offset = int(3 * s)
    def rot_sh(bx, by):
        c, sv = math.cos(angle), math.sin(angle)
        return (cx + bx*c - by*sv + shadow_offset,
                cy + bx*sv + by*c + shadow_offset)

    # ── Gövde ────────────────────────────────────────────────────────────────
    nose_tip = pw
    tail_end = -pw * 0.88

    body_shadow = [
        rot_sh(tail_end,  body_h * 0.5),
        rot_sh(nose_tip * 0.9, body_h * 0.0),
        rot_sh(nose_tip,  0),
        rot_sh(nose_tip * 0.9, -body_h * 0.0),
        rot_sh(tail_end, -body_h * 0.5),
    ]
    draw.polygon(body_shadow, fill=(0, 0, 0, 50))

    body = [
        rot(tail_end,  body_h * 0.5),
        rot(nose_tip * 0.9, body_h * 0.15),
        rot(nose_tip,  0),
        rot(nose_tip * 0.9, -body_h * 0.15),
        rot(tail_end, -body_h * 0.5),
    ]
    draw.polygon(body, fill=(255, 255, 255, 255))

    # ── Ana kanat ────────────────────────────────────────────────────────────
    main_wing = [
        rot(-pw * 0.08,  body_h * 0.15),
        rot( pw * 0.28, -wing_h),
        rot( pw * 0.28 + wing_w * 0.5, -wing_h * 0.15),
        rot( pw * 0.55,  body_h * 0.1),
    ]
    draw.polygon(main_wing, fill=(220, 228, 255, 245))

    # Alt kanat (simetrik)
    main_wing_bot = [
        rot(-pw * 0.08, -body_h * 0.15),
        rot( pw * 0.28,  wing_h),
        rot( pw * 0.28 + wing_w * 0.5,  wing_h * 0.15),
        rot( pw * 0.55, -body_h * 0.1),
    ]
    draw.polygon(main_wing_bot, fill=(200, 212, 255, 200))

    # ── Kuyruk kanadı ────────────────────────────────────────────────────────
    tail_top = [
        rot(-pw * 0.68, body_h * 0.4),
        rot(-pw * 0.35, -tail_h),
        rot(-pw * 0.10, body_h * 0.3),
    ]
    draw.polygon(tail_top, fill=(210, 222, 255, 230))

    tail_bot = [
        rot(-pw * 0.68, -body_h * 0.4),
        rot(-pw * 0.35,  tail_h),
        rot(-pw * 0.10, -body_h * 0.3),
    ]
    draw.polygon(tail_bot, fill=(190, 205, 255, 200))

    # Gövde üzeri çizgi (cockpit detay — büyük boyutlarda)
    if size >= 48:
        window_col = (180, 200, 255, 160)
        ww = max(1, int(1.5 * s))
        draw.line([rot(pw * 0.5, -body_h * 0.08),
                   rot(pw * 0.78, -body_h * 0.04)],
                  fill=window_col, width=ww)

    return img


def build_ico(sizes):
    frames = []
    for sz in sorted(sizes, reverse=True):
        buf = io.BytesIO()
        make_frame(sz).save(buf, format="PNG")
        frames.append((sz, buf.getvalue()))

    n      = len(frames)
    header = struct.pack("<HHH", 0, 1, n)
    offset = 6 + n * 16
    entries = b""
    images  = b""
    for sz, png_data in frames:
        w = sz if sz < 256 else 0
        h = sz if sz < 256 else 0
        entries += struct.pack("<BBBBHHII",
            w, h, 0, 0, 1, 32, len(png_data), offset + len(images))
        images  += png_data
    return header + entries + images


out = r"C:\Users\ilayd\OneDrive\Desktop\SmartTravelAI\smarttravel.ico"
data = build_ico([16, 24, 32, 48, 64, 128, 256])
with open(out, "wb") as f:
    f.write(data)

import os
print(f"ICO: {out}  —  {os.path.getsize(out):,} byte")
