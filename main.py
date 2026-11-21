#!/usr/bin/env python3
"""HOVERBREW - catalogue photograph of an impossible gadget.

Pure-stdlib renderer (zlib + struct PNG encoder). Deterministic.
Writes /output/entry.png (1024x1024).
"""
import math
import os
import struct
import zlib

W = H = 1024
OUT = "/output/entry.png"

# ---------- framebuffer ----------
# rows of bytearray, RGB
img = [bytearray(W * 3) for _ in range(H)]


def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


def blend(px, r, g, b, a):
    """Blend color over pixel px (byte offset) with alpha 0..1."""
    if a <= 0:
        return
    if a >= 1:
        img_px = px
        # handled by caller via direct set; here generic
    ia = 1.0 - a
    img[py][px] = int(r * a + img[py][px] * ia)
    img[py][px + 1] = int(g * a + img[py][px + 1] * ia)
    img[py][px + 2] = int(b * a + img[py][px + 2] * ia)


# ---------- background: warm grey vertical gradient + vignette ----------
# top (235,232,226) -> bottom (198,194,188)
for y in range(H):
    t = y / (H - 1)
    br = 235 + (198 - 235) * t
    bg = 232 + (194 - 232) * t
    bb = 226 + (188 - 226) * t
    row = img[y]
    # vignette: darken toward corners
    dy = (y - 512) / 512.0
    for x in range(W):
        dx = (x - 512) / 512.0
        d2 = dx * dx + dy * dy
        vig = 1.0 - 0.10 * d2
        o = x * 3
        row[o] = int(br * vig)
        row[o + 1] = int(bg * vig)
        row[o + 2] = int(bb * vig)

py = 0  # current row for blend()


def ell_alpha(x, y, cx, cy, rx, ry):
    """Smooth elliptical falloff 1 at centre -> 0 at edge."""
    dx = (x - cx) / rx
    dy = (y - cy) / ry
    d2 = dx * dx + dy * dy
    if d2 >= 1.0:
        return 0.0
    d = math.sqrt(d2)
    # smooth edge
    a = 1.0 - d * d
    return a * a


def draw_soft_ellipse(cx, cy, rx, ry, r, g, b, alpha, x0=None, x1=None, y0=None, y1=None):
    global py
    x0 = max(0, int(cx - rx) if x0 is None else x0)
    x1 = min(W - 1, int(cx + rx) if x1 is None else x1)
    y0 = max(0, int(cy - ry) if y0 is None else y0)
    y1 = min(H - 1, int(cy + ry) if y1 is None else y1)
    for y in range(y0, y1 + 1):
        py = y
        row = img[y]
        dy = (y - cy) / ry
        for x in range(x0, x1 + 1):
            dx = (x - cx) / rx
            d2 = dx * dx + dy * dy
            if d2 >= 1.0:
                continue
            d = math.sqrt(d2)
            a = (1.0 - d * d) ** 2 * alpha
            o = x * 3
            ia = 1.0 - a
            row[o] = int(r * a + row[o] * ia)
            row[o + 1] = int(g * a + row[o + 1] * ia)
            row[o + 2] = int(b * a + row[o + 2] * ia)


# ---------- soft shadows ----------
draw_soft_ellipse(512, 905, 260, 34, 60, 55, 50, 0.35)   # mug shadow
draw_soft_ellipse(790, 920, 120, 18, 60, 55, 50, 0.28)   # spoon shadow

# ---------- spoon (single accessory, bottom-right, lying flat) ----------
# handle: rotated rounded bar from bowl toward lower-right
def draw_spoon():
    global py
    # bowl ellipse, tilted
    cx, cy, rx, ry, ang = 745, 868, 52, 30, -0.5
    ca, sa = math.cos(ang), math.sin(ang)
    for y in range(cy - 55, cy + 56):
        if y < 0 or y >= H:
            continue
        py = y
        row = img[y]
        for x in range(cx - 60, cx + 61):
            if x < 0 or x >= W:
                continue
            lx = (x - cx) * ca + (y - cy) * sa
            ly = -(x - cx) * sa + (y - cy) * ca
            d2 = (lx / rx) ** 2 + (ly / ry) ** 2
            if d2 >= 1.0:
                continue
            # metallic gradient: bright centre-left
            t = max(0.0, min(1.0, 0.5 - lx / (2 * rx) + 0.35 * (1 - ly / ry)))
            r = 200 + 45 * t
            g = 200 + 45 * t
            b = 205 + 40 * t
            # inner bowl shading
            inner = (lx / (rx * 0.7)) ** 2 + (ly / (ry * 0.7)) ** 2
            if inner < 1.0:
                r *= 0.82
                g *= 0.82
                b *= 0.85
            # soft edge AA
            d = math.sqrt(d2)
            a = 1.0 if d < 0.92 else (1.0 - d) / 0.08
            o = x * 3
            ia = 1.0 - a
            row[o] = int(r * a + row[o] * ia)
            row[o + 1] = int(g * a + row[o + 1] * ia)
            row[o + 2] = int(b * a + row[o + 2] * ia)
    # handle: rotated bar from bowl edge to (905, 930)
    hx0, hy0, hx1, hy1 = 780, 885, 920, 935
    ang = math.atan2(hy1 - hy0, hx1 - hx0)
    ca, sa = math.cos(ang), math.sin(ang)
    length = math.hypot(hx1 - hx0, hy1 - hy0)
    half_w = 9
    for y in range(min(hy0, hy1) - 14, max(hy0, hy1) + 15):
        if y < 0 or y >= H:
            continue
        py = y
        row = img[y]
        for x in range(min(hx0, hx1) - 14, max(hx0, hx1) + 15):
            if x < 0 or x >= W:
                continue
            lx = (x - hx0) * ca + (y - hy0) * sa
            ly = -(x - hx0) * sa + (y - hy0) * ca
            if lx < -4 or lx > length + 4 or abs(ly) > half_w + 1:
                continue
            edge = max(0.0, abs(ly) - (half_w - 1))
            a = 1.0 if edge <= 0 else max(0.0, 1.0 - edge)
            t = 0.5 - ly / (2 * half_w)
            r = 205 + 40 * t
            g = 205 + 40 * t
            b = 210 + 35 * t
            o = x * 3
            ia = 1.0 - a
            row[o] = int(r * a + row[o] * ia)
            row[o + 1] = int(g * a + row[o + 1] * ia)
            row[o + 2] = int(b * a + row[o + 2] * ia)


draw_spoon()

# ---------- mug body ----------
# body: x 372..652, y 560..884, rounded bottom corners r=28
MX0, MX1, MY0, MY1 = 372, 652, 560, 884
for y in range(MY0, MY1 + 1):
    py = y
    row = img[y]
    # bottom rounding
    if y > MY1 - 28:
        dy = y - (MY1 - 28)
        cut = 28 - math.sqrt(max(0.0, 28 * 28 - dy * dy))
    else:
        cut = 0.0
    for x in range(MX0, MX1 + 1):
        if x < MX0 + cut or x > MX1 - cut:
            continue
        # vertical gradient: left bright -> right darker (studio light from left)
        t = (x - MX0) / (MX1 - MX0)
        base = 252 - 52 * t
        # soft vertical highlight band on left third
        hl = 14 * math.exp(-((x - 415) ** 2) / (2 * 26.0 ** 2))
        # subtle vertical shading: slightly darker near bottom
        shade = 1.0 - 0.05 * (y - MY0) / (MY1 - MY0)
        r = clamp((base + hl) * shade)
        g = clamp((base + hl - 2) * shade)
        b = clamp((base + hl - 6) * shade)
        o = x * 3
        row[o] = int(r)
        row[o + 1] = int(g)
        row[o + 2] = int(b)

# mug top rim: outer ellipse + inner coffee surface
# rim highlight ring
for y in range(536, 585):
    py = y
    row = img[y]
    for x in range(360, 665):
        dx = (x - 512) / 140.0
        dy = (y - 560) / 24.0
        d2 = dx * dx + dy * dy
        if d2 > 1.05 or d2 < 0.55:
            continue
        # rim ceramic bright
        t = (x - 372) / 280.0
        v = 250 - 45 * t
        a = 1.0 if d2 <= 1.0 else max(0.0, (1.05 - d2) / 0.05)
        o = x * 3
        ia = 1.0 - a
        row[o] = int(v * a + row[o] * ia)
        row[o + 1] = int((v - 2) * a + row[o + 1] * ia)
        row[o + 2] = int((v - 6) * a + row[o + 2] * ia)
# inner coffee surface (dark ellipse)
draw_soft_ellipse(512, 560, 118, 17, 46, 26, 16, 0.95)
# coffee sheen arc on surface
draw_soft_ellipse(480, 556, 55, 7, 96, 62, 38, 0.5)

# ---------- mug handle (right side, ring arc) ----------
HCX, HCY, HR, HT = 668, 716, 78, 24
for y in range(HCY - HR - HT, HCY + HR + HT + 1):
    if y < 0 or y >= H:
        continue
    py = y
    row = img[y]
    for x in range(HCX - 30, HCX + HR + HT + 1):
        if x < 0 or x >= W:
            continue
        dx = x - HCX
        dy = y - HCY
        dist = math.hypot(dx, dy)
        if dist < HR - HT / 2 or dist > HR + HT / 2:
            continue
        # only outer half of ring (right side), attach to mug
        if dx < -10:
            continue
        # ceramic shading: brighter top
        t = 0.5 - dy / (2 * HR)
        v = 246 - 50 * t
        # AA on ring edges
        edge = min(abs(dist - (HR - HT / 2)), abs(dist - (HR + HT / 2)))
        a = 1.0 if edge > 1.0 else edge
        o = x * 3
        ia = 1.0 - a
        row[o] = int(v * a + row[o] * ia)
        row[o + 1] = int((v - 2) * a + row[o + 1] * ia)
        row[o + 2] = int((v - 6) * a + row[o + 2] * ia)

# ---------- levitating coffee sphere ----------
SCX, SCY, SR = 512, 372, 108
for y in range(SCY - SR - 2, SCY + SR + 3):
    if y < 0 or y >= H:
        continue
    py = y
    row = img[y]
    for x in range(SCX - SR - 2, SCX + SR + 3):
        if x < 0 or x >= W:
            continue
        dx = (x - SCX) / SR
        dy = (y - SCY) / SR
        d2 = dx * dx + dy * dy
        if d2 >= 1.0:
            continue
        d = math.sqrt(d2)
        # sphere shading: light from upper-left
        lx, ly = -0.55, -0.65
        lam = max(0.0, -(dx * lx + dy * ly))
        base = 52 + 62 * lam
        # rim darkening at sphere edge
        rim = 1.0 - 0.55 * (d ** 3)
        r = clamp(base * rim + 8)
        g = clamp((base * 0.62 + 4) * rim + 4)
        b = clamp((base * 0.38 + 2) * rim + 2)
        # glossy specular highlight upper-left
        hx, hy = -0.42, -0.48
        hd = math.hypot(dx - hx, dy - hy)
        spec = math.exp(-(hd ** 2) / (2 * 0.10 ** 2))
        r = clamp(r + 200 * spec)
        g = clamp(g + 200 * spec)
        b = clamp(b + 195 * spec)
        # secondary soft sheen lower-right
        sx, sy = 0.45, 0.55
        sd = math.hypot(dx - sx, dy - sy)
        sheen = math.exp(-(sd ** 2) / (2 * 0.22 ** 2)) * 0.35
        r = clamp(r + 60 * sheen)
        g = clamp(g + 38 * sheen)
        b = clamp(b + 22 * sheen)
        # AA edge
        a = 1.0 if d < 0.97 else (1.0 - d) / 0.03
        o = x * 3
        ia = 1.0 - a
        row[o] = int(r * a + row[o] * ia)
        row[o + 1] = int(g * a + row[o + 1] * ia)
        row[o + 2] = int(b * a + row[o + 2] * ia)

# small white specular dot
draw_soft_ellipse(468, 322, 10, 7, 255, 255, 250, 0.9)

# ---------- levitating droplets between sphere and mug ----------
def droplet(cx, cy, r):
    for y in range(int(cy - r - 2), int(cy + r + 3)):
        if y < 0 or y >= H:
            continue
        py = y
        row = img[y]
        for x in range(int(cx - r - 2), int(cx + r + 3)):
            if x < 0 or x >= W:
                continue
            dx = (x - cx) / r
            dy = (y - cy) / r
            d2 = dx * dx + dy * dy
            if d2 >= 1.0:
                continue
            d = math.sqrt(d2)
            lam = max(0.0, -(-0.55 * dx + -0.65 * dy))
            base = 55 + 60 * lam
            rr = clamp(base * (1 - 0.5 * d ** 3))
            gg = clamp(base * 0.62)
            bb = clamp(base * 0.38)
            hd = math.hypot(dx + 0.4, dy + 0.45)
            spec = math.exp(-(hd ** 2) / (2 * 0.12 ** 2))
            rr = clamp(rr + 200 * spec)
            gg = clamp(gg + 200 * spec)
            bb = clamp(bb + 195 * spec)
            a = 1.0 if d < 0.9 else (1.0 - d) / 0.1
            o = x * 3
            ia = 1.0 - a
            row[o] = int(rr * a + row[o] * ia)
            row[o + 1] = int(gg * a + row[o + 1] * ia)
            row[o + 2] = int(bb * a + row[o + 2] * ia)


droplet(512, 512, 13)
droplet(548, 540, 8)

# ---------- thin steam curls rising from the sphere ----------
def steam(cx0, phase, amp, alpha):
    # wavy vertical line from y=250 up to y=120
    for y in range(120, 262):
        t = (262 - y) / 142.0
        cx = cx0 + amp * math.sin(t * 5.0 + phase) * t
        for x in range(int(cx - 6), int(cx + 7)):
            if x < 0 or x >= W:
                continue
            d = abs(x - cx)
            a = math.exp(-(d ** 2) / (2 * 2.2 ** 2)) * alpha * (0.4 + 0.6 * t)
            o = x * 3
            row = img[y]
            ia = 1.0 - a
            row[o] = int(255 * a + row[o] * ia)
            row[o + 1] = int(255 * a + row[o + 1] * ia)
            row[o + 2] = int(255 * a + row[o + 2] * ia)


steam(470, 0.0, 14, 0.30)
steam(512, 1.6, 12, 0.26)
steam(556, 3.1, 13, 0.28)

# ---------- "HOVERBREW" text on mug body (5x7 bitmap font, scale 3) ----------
FONT = {
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "W": ["#...#", "#...#", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."],
}
TEXT = "HOVERBREW"
SCALE = 3
CW, CH, GAP = 5 * SCALE, 7 * SCALE, 1 * SCALE
tw = len(TEXT) * CW + (len(TEXT) - 1) * GAP
tx0 = MX0 + (MX1 - MX0 - tw) // 2
ty0 = 690
for i, ch in enumerate(TEXT):
    glyph = FONT[ch]
    gx = tx0 + i * (CW + GAP)
    for gy in range(7):
        for gx_ in range(5):
            if glyph[gy][gx_] != "#":
                continue
            for sy in range(SCALE):
                y = ty0 + gy * SCALE + sy
                row = img[y]
                for sx in range(SCALE):
                    x = gx + gx_ * SCALE + sx
                    o = x * 3
                    row[o] = 58
                    row[o + 1] = 52
                    row[o + 2] = 48

# ---------- PNG encode (stdlib only) ----------
def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return c


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter None
        raw.extend(img[y])
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(OUT, "wb") as f:
        f.write(png)
    print("wrote", OUT, len(png), "bytes")


if __name__ == "__main__":
    main()
