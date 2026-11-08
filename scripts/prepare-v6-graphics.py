"""Prepare the Lions Park v6 brand media textures.

v6 replaces the generic victory collage with the club's own catchphrase and the
real ballpark sponsor line-up:

  * WIN OR WOW            official Samsung Lions 2026 catchphrase
  * 혼연일체               squad slogan ("one body, one heart")
  * DGB대구은행(iM뱅크) · POSCO · 삼성생명 · 삼성화재 · Galaxy · 에버랜드 ·
    참소주 · 금복주   the outfield fence sponsor boards of Daegu Samsung Lions Park
  * 블레오 · 핑크레오 · 레니 · 라온   the Bleo mascot family
  * 지적도 151,526.00 ㎡  the official parcel, drawn as a cadastral plan board

Everything here is drawn from scratch with Pillow + the bundled OFL fonts, so the
artwork is original to this repository and safe to redistribute under MIT. Brand
names are rendered as plain lettering on a sponsor board, the way a ground hoarding
is reconstructed in an architectural model; no club or company logo file is copied.

Run with a normal CPython that has Pillow installed:

    python3 scripts/prepare-v6-graphics.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "blender" / "textures"
OUT.mkdir(parents=True, exist_ok=True)
FONTS = ROOT / "assets" / "blender" / "fonts"

DISPLAY = FONTS / "BarlowCondensed-Bold.ttf"
BOLD = FONTS / "NotoSansKR.ttf"

NAVY = (8, 24, 58)
DEEP = (4, 12, 30)
LIONS_BLUE = (0, 102, 178)
ICE = (188, 214, 240)
WHITE = (247, 250, 255)
GOLD = (216, 166, 58)
PINK = (240, 122, 168)
SUN = (246, 199, 68)
MINT = (86, 198, 190)


def font(path: Path, size: int, weight: str | None = None) -> ImageFont.FreeTypeFont:
    face = ImageFont.truetype(str(path), size)
    if weight:
        # Noto Sans KR ships as a variable font whose default instance is Thin.
        try:
            face.set_variation_by_name(weight.encode())
        except (OSError, ValueError):
            pass
    return face


def kfont(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    return font(BOLD, size, weight)


def fit(draw: ImageDraw.ImageDraw, body: str, path: Path, size: int, width: int, gap: int = 8):
    """Shrink the point size until the text fits inside `width`."""
    while size > gap:
        probe = fit_font(path, size)
        if draw.textlength(body, font=probe) <= width:
            return probe
        size -= 2
    return fit_font(path, gap)


def fit_font(path: Path, size: int):
    return font(path, size, "Bold" if path == BOLD else None)


def text(draw, xy, body, path, size, fill, width=None, anchor="la", spacing=0, stroke=0):
    use = fit(draw, body, path, size, width) if width else fit_font(path, size)
    if stroke:
        draw.text(xy, body, font=use, fill=fill, anchor=anchor, spacing=spacing,
                  stroke_width=stroke, stroke_fill=fill)
    draw.text(xy, body, font=use, fill=fill, anchor=anchor, spacing=spacing)
    return use


def vgradient(size, top, bottom):
    width, height = size
    canvas = Image.new("RGB", (1, height))
    for y in range(height):
        t = y / max(1, height - 1)
        canvas.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return canvas.resize((width, height), Image.BILINEAR)


def radial(size, center, radius, color, strength=1.0):
    width, height = size
    glow = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(glow)
    cx, cy = center
    steps = 26
    for i in range(steps, 0, -1):
        t = i / steps
        draw.ellipse(
            [cx - radius * t, cy - radius * t * 0.75, cx + radius * t, cy + radius * t * 0.75],
            fill=int(255 * strength * (1 - t) ** 1.5),
        )
    glow = glow.filter(ImageFilter.GaussianBlur(radius * 0.06))
    layer = Image.new("RGB", (width, height), color)
    return layer, glow


def led_grid(canvas: Image.Image, cell: int = 6, strength: float = 0.18) -> Image.Image:
    width, height = canvas.size
    grid = Image.new("RGB", canvas.size, (0, 0, 0))
    draw = ImageDraw.Draw(grid)
    for x in range(0, width, cell):
        draw.line([(x, 0), (x, height)], fill=(12, 14, 20))
    for y in range(0, height, cell):
        draw.line([(0, y), (width, y)], fill=(12, 14, 20))
    grid = grid.filter(ImageFilter.GaussianBlur(cell * 0.12))
    return Image.blend(canvas, grid, strength)


def vignette(canvas: Image.Image, amount: float = 0.35) -> Image.Image:
    width, height = canvas.size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse(
        [-width * 0.12, -height * 0.3, width * 1.12, height * 1.3], fill=255
    )
    mask = mask.filter(ImageFilter.GaussianBlur(width * 0.04))
    dark = Image.new("RGB", (width, height), (0, 0, 0))
    return Image.composite(canvas, dark, mask.point(lambda v: int(255 - amount * 255 + v * amount)))


def draw_lion(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, body, mane, jersey, number: str):
    """A chibi club mascot: mane, head, muzzle, eyes, grin and a jersey."""
    # body
    draw.rounded_rectangle(
        [cx - r * 0.72, cy + r * 0.55, cx + r * 0.72, cy + r * 1.75],
        radius=int(r * 0.5),
        fill=jersey,
    )
    # arms
    for sign in (-1, 1):
        draw.ellipse(
            [cx + sign * r * 0.86 - r * 0.22, cy + r * 0.68, cx + sign * r * 0.86 + r * 0.22, cy + r * 1.2],
            fill=body,
        )
    # mane
    for k in range(14):
        angle = k * math.tau / 14
        mx = cx + math.cos(angle) * r * 0.86
        my = cy - r * 0.12 + math.sin(angle) * r * 0.86
        draw.ellipse([mx - r * 0.3, my - r * 0.3, mx + r * 0.3, my + r * 0.3], fill=mane)
    # head
    draw.ellipse([cx - r * 0.78, cy - r * 0.9, cx + r * 0.78, cy + r * 0.66], fill=body)
    # ears
    for sign in (-1, 1):
        ex = cx + sign * r * 0.6
        ey = cy - r * 0.82
        draw.ellipse([ex - r * 0.24, ey - r * 0.26, ex + r * 0.24, ey + r * 0.2], fill=body)
        draw.ellipse([ex - r * 0.12, ey - r * 0.13, ex + r * 0.12, ey + r * 0.1], fill=mane)
    # muzzle
    draw.ellipse([cx - r * 0.46, cy + r * 0.05, cx + r * 0.46, cy + r * 0.6], fill=(255, 250, 244))
    draw.polygon(
        [(cx - r * 0.13, cy + r * 0.18), (cx + r * 0.13, cy + r * 0.18), (cx, cy + r * 0.32)],
        fill=(34, 32, 38),
    )
    draw.arc([cx - r * 0.22, cy + r * 0.2, cx, cy + r * 0.46], 20, 160, fill=(34, 32, 38), width=max(2, r // 22))
    draw.arc([cx, cy + r * 0.2, cx + r * 0.22, cy + r * 0.46], 20, 160, fill=(34, 32, 38), width=max(2, r // 22))
    # eyes
    for sign in (-1, 1):
        ex = cx + sign * r * 0.34
        ey = cy - r * 0.28
        draw.ellipse([ex - r * 0.15, ey - r * 0.19, ex + r * 0.15, ey + r * 0.19], fill=(250, 250, 252))
        draw.ellipse([ex - r * 0.09, ey - r * 0.1, ex + r * 0.09, ey + r * 0.12], fill=(28, 30, 40))
        draw.ellipse([ex - r * 0.05, ey - r * 0.07, ex + r * 0.0, ey - r * 0.01], fill=(255, 255, 255))
    # jersey number
    if number:
        size = max(18, int(r * 0.5))
        nf = fit_font(DISPLAY, size)
        draw.text((cx, cy + r * 1.18), number, font=nf, fill=WHITE, anchor="mm")


# ---------------------------------------------------------------------------
# 1. Main outfield scoreboard (36.0 m x 20.4 m -> 3840 x 2176)
# ---------------------------------------------------------------------------
def build_scoreboard() -> None:
    width, height = 3840, 2176
    canvas = vgradient((width, height), (11, 30, 70), (3, 10, 26))
    glow, mask = radial((width, height), (900, 640), 1500, (0, 84, 168), 1.0)
    canvas = Image.composite(glow, canvas, mask)
    draw = ImageDraw.Draw(canvas)

    # header
    draw.rectangle([0, 0, width, 176], fill=(6, 17, 42))
    text(draw, (96, 88), "SAMSUNG LIONS", DISPLAY, 108, WHITE, anchor="lm")
    text(draw, (width - 96, 84), "대구 삼성 라이온즈 파크", BOLD, 66, ICE, anchor="rm")
    draw.rectangle([0, 176, width, 184], fill=LIONS_BLUE)

    # hero catchphrase, measured so nothing collides
    hero = fit(draw, "WIN OR WOW", DISPLAY, 400, 2180)
    draw.text((96, 250), "WIN OR WOW", font=hero, fill=WHITE, anchor="lt")
    hero_box = draw.textbbox((96, 250), "WIN OR WOW", font=hero)
    rule_y = hero_box[3] + 26
    draw.rectangle([100, rule_y, 2300, rule_y + 18], fill=LIONS_BLUE)
    text(draw, (100, rule_y + 58), "혼연일체", BOLD, 150, GOLD, stroke=4)
    text(draw, (100, rule_y + 250), "ONE TEAM, ONE HEART", DISPLAY, 92, ICE, width=2200)
    text(draw, (100, rule_y + 370), "2026 KBO LEAGUE  ·  DAEGU SAMSUNG LIONS PARK", DISPLAY, 58, (150, 180, 215), width=2200)

    # fixture strip under the hero block
    info_y = rule_y + 470
    draw.rounded_rectangle([100, info_y, 2280, info_y + 210], radius=18, fill=(7, 20, 46), outline=(26, 62, 108), width=3)
    text(draw, (140, info_y + 46), "오늘의 경기  ·  SAMSUNG LIONS  vs  롯데 자이언츠", BOLD, 58, WHITE, width=2080, stroke=1)
    text(draw, (140, info_y + 128), "2026.09.12 (토) 17:00  ·  사직야구장  ·  관중 22,418", BOLD, 44, (150, 180, 215), width=2080)
    text(draw, (100, info_y + 300), "WIN OR WOW — 이겨도, 감탄하게.  혼연일체로 오늘을 함께합니다.", BOLD, 54, GOLD, width=2200, stroke=1)

    # live score panel on the right
    draw.rounded_rectangle([2380, 250, width - 72, 1700], radius=28, fill=(7, 18, 40), outline=(30, 74, 130), width=4)
    draw.rounded_rectangle([2380, 250, width - 72, 400], radius=28, fill=(10, 30, 68))
    text(draw, (2432, 326), "7회말  ·  홈", BOLD, 80, GOLD, anchor="lm")
    text(draw, (width - 120, 326), "사직구장", BOLD, 62, ICE, anchor="rm")
    headings = ["팀", "1", "2", "3", "4", "5", "6", "7", "8", "9", "R", "H", "E"]
    left, right = 2400, width - 96
    step = (right - left) / len(headings)
    for index, head in enumerate(headings):
        x = left + step * (index + 0.5)
        head_font = fit(draw, head, BOLD if head == "팀" else DISPLAY, 60, int(step * 0.9))
        draw.text((x, 470), head, font=head_font, fill=(150, 178, 210), anchor="mm")
    draw.line([left, 510, right, 510], fill=(28, 60, 104), width=3)
    rows = [
        ("LIONS", ["0", "1", "0", "2", "0", "0", "1", "", "", "", "4", "9", "0"], WHITE),
        ("상대팀", ["0", "0", "1", "0", "0", "1", "", "", "", "", "2", "6", "1"], ICE),
    ]
    for row_index, (team, cells, colour) in enumerate(rows):
        y = 600 + row_index * 150
        if row_index:
            draw.line([left, y - 74, right, y - 74], fill=(24, 52, 92), width=3)
        for index, cell in enumerate(cells):
            x = left + step * (index + 0.5)
            if index == 0:
                use = fit(draw, team, BOLD, 62, int(step * 0.98))
            else:
                use = fit_font(DISPLAY, 92)
            draw.text((x, y), cell if index else team, font=use, fill=colour, anchor="mm")
    # inning marker under the line score
    draw.rounded_rectangle([2420, 800, width - 116, 900], radius=16, fill=(12, 40, 88))
    text(draw, (2452, 850), "현재 7회말  ·  LIONS 공격", BOLD, 52, ICE, anchor="lm")
    # batter / pitcher / count
    draw.rounded_rectangle([2400, 930, width - 96, 1660], radius=22, fill=(8, 22, 48))
    text(draw, (2448, 990), "타자  김헌곤  (중견수)", BOLD, 64, WHITE)
    text(draw, (2448, 1064), "타율 .312   ·   5홈런   ·   41타점", BOLD, 46, (150, 180, 215))
    draw.line([2448, 1140, width - 146, 1140], fill=(24, 52, 92), width=3)
    text(draw, (2448, 1190), "투수  원태인", BOLD, 64, WHITE)
    text(draw, (2448, 1264), "평균자책 2.87   ·   132탈삼진", BOLD, 46, (150, 180, 215))
    draw.line([2448, 1340, width - 146, 1340], fill=(24, 52, 92), width=3)
    for k, label in enumerate("BSO"):
        cx = 2500 + k * 170
        on = k == 1
        draw.ellipse([cx - 52, 1392, cx + 52, 1496], outline=(40, 92, 150), width=6)
        if on:
            draw.ellipse([cx - 40, 1404, cx + 40, 1484], fill=GOLD)
        text(draw, (cx, 1556), label, DISPLAY, 66, GOLD if on else (90, 120, 155), anchor="mm")
    text(draw, (width - 200, 1444), "2-2", DISPLAY, 96, WHITE, anchor="mm")
    text(draw, (width - 200, 1560), "COUNT", DISPLAY, 44, (120, 152, 190), anchor="mm")

    # bottom ticker
    draw.rectangle([0, 1746, width, height], fill=(5, 14, 34))
    draw.rectangle([0, 1746, width, 1756], fill=LIONS_BLUE)
    ticker = "WIN OR WOW  ·  혼연일체  ·  오늘도 라팍에서 함께합니다  ·  VAMOS LIONS  ·  "
    text(draw, (96, 1850), ticker * 3, BOLD, 68, WHITE, width=width - 192, anchor="lt")
    text(draw, (96, 2010), "DAEGU SAMSUNG LIONS PARK  ·  36.0 m × 20.4 m LED  ·  WIN OR WOW", DISPLAY, 52, (140, 172, 208))
    text(draw, (width - 96, 2010), "WIN OR WOW", DISPLAY, 74, GOLD, anchor="ra")

    canvas = led_grid(canvas, 6, 0.16)
    canvas = vignette(canvas, 0.24)
    canvas.save(OUT / "brand-scoreboard-winorwow.jpg", quality=94)


# ---------------------------------------------------------------------------
# 2. Outfield fence murals
# ---------------------------------------------------------------------------
def build_fence_murals() -> None:
    width, height = 4096, 1024
    # WIN OR WOW mural
    canvas = vgradient((width, height), (12, 34, 78), (5, 14, 38))
    glow, mask = radial((width, height), (1500, 520), 1300, (0, 96, 190), 1.0)
    canvas = Image.composite(glow, canvas, mask)
    draw = ImageDraw.Draw(canvas)
    for k in range(9):
        x = 300 + k * 430
        draw.line([(x, -100), (x - 420, height + 100)], fill=(255, 255, 255), width=2)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rectangle([0, 0, width, height], fill=(4, 14, 36, 130))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    hero = fit(draw, "WIN OR WOW", DISPLAY, 470, 2760)
    draw.text((170, 210), "WIN OR WOW", font=hero, fill=WHITE, anchor="lt")
    box = draw.textbbox((170, 210), "WIN OR WOW", font=hero)
    rule = box[3] + 22
    draw.rectangle([176, rule, 2900, rule + 16], fill=LIONS_BLUE)
    text(draw, (176, rule + 54), "대구 삼성 라이온즈 파크  ·  DAEGU SAMSUNG LIONS PARK", BOLD, 74, ICE, width=2600, stroke=1)
    # crest roundel
    cx, cy, r = 3480, 470, 300
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(8, 28, 66), outline=GOLD, width=12)
    draw.polygon(
        [(cx, cy - 190), (cx + 150, cy - 60), (cx + 96, cy + 150), (cx, cy + 196), (cx - 96, cy + 150), (cx - 150, cy - 60)],
        fill=LIONS_BLUE,
    )
    text(draw, (cx, cy + 6), "LIONS", DISPLAY, 168, WHITE, anchor="mm")
    text(draw, (cx, cy + 300), "SAMSUNG", DISPLAY, 66, GOLD, anchor="mm")
    canvas = led_grid(canvas, 8, 0.1)
    canvas.save(OUT / "brand-fence-winorwow.jpg", quality=93)

    # 혼연일체 mural
    canvas = vgradient((width, height), (7, 20, 48), (16, 44, 96))
    draw = ImageDraw.Draw(canvas)
    for k in range(26):
        y = k * 44
        draw.line([(0, y), (width, y)], fill=(255, 255, 255), width=1)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rectangle([0, 0, width, height], fill=(6, 20, 46, 150))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    hero = fit(draw, "혼연일체", BOLD, 420, 2100)
    draw.text((200, 150), "혼연일체", font=hero, fill=GOLD, anchor="lt", stroke_width=8, stroke_fill=GOLD)
    draw.text((200, 150), "혼연일체", font=hero, fill=GOLD, anchor="lt")
    box = draw.textbbox((200, 150), "혼연일체", font=hero)
    text(draw, (215, box[3] + 40), "ONE TEAM.  ONE HEART.", DISPLAY, 132, WHITE, width=2050)
    text(draw, (220, box[3] + 200), "VAMOS LIONS  ·  2026", DISPLAY, 70, ICE, width=1500)
    draw.rounded_rectangle([2700, 180, 3900, 860], radius=40, outline=GOLD, width=8)
    text(draw, (3300, 360), "우리는", BOLD, 96, ICE, anchor="mm", stroke=3)
    text(draw, (3300, 520), "하나입니다", BOLD, 108, WHITE, anchor="mm", stroke=3)
    text(draw, (3300, 720), "WIN OR WOW", DISPLAY, 104, GOLD, anchor="mm")
    canvas.save(OUT / "brand-fence-honyeonilche.jpg", quality=93)


# ---------------------------------------------------------------------------
# 3. Sponsor hoardings (outfield wall + concourse fascia)
# ---------------------------------------------------------------------------
def build_sponsors() -> None:
    width, height = 4096, 1024
    canvas = Image.new("RGB", (width, height), (10, 12, 18))
    draw = ImageDraw.Draw(canvas)
    boards = [
        ("DGB 대구은행", "iM뱅크", (255, 255, 255), (11, 58, 120), (0, 72, 150)),
        ("POSCO", "STEEL FOR THE FUTURE", (250, 250, 250), (8, 46, 96), (0, 88, 160)),
        ("삼성생명", "SAMSUNG LIFE", (255, 255, 255), (0, 62, 148), (0, 110, 196)),
        ("삼성화재", "SAMSUNG FIRE", (255, 255, 255), (4, 44, 110), (10, 92, 178)),
        ("Galaxy", "SAMSUNG", (18, 18, 22), (206, 214, 228), (120, 132, 152)),
        ("에버랜드", "EVERLAND", (255, 255, 255), (18, 104, 62), (56, 158, 96)),
        ("참소주", "CHAM SOJU", (255, 255, 255), (168, 28, 36), (214, 62, 54)),
        ("금복주", "KUMBOKJU", (252, 246, 232), (140, 26, 32), (188, 58, 48)),
    ]
    span = width // len(boards)
    for index, (name, sub, bg, ink, accent) in enumerate(boards):
        x0 = index * span
        draw.rectangle([x0, 0, x0 + span - 6, height], fill=bg)
        draw.rectangle([x0, height - 96, x0 + span - 6, height], fill=accent)
        text(draw, (x0 + span // 2, 420), name, BOLD, 108, ink, width=span - 90, anchor="mm")
        sub_font = BOLD if any("\uac00" <= ch <= "\ud7a3" for ch in sub) else DISPLAY
        use = fit(draw, sub, sub_font, 72, span - 130)
        draw.text((x0 + span // 2, 600), sub, font=use, fill=accent if bg[0] > 100 else ink, anchor="mm")
        draw.rectangle([x0 + 40, 96, x0 + span - 46, 104], fill=accent)
    canvas.save(OUT / "brand-fence-sponsors.jpg", quality=93)


# ---------------------------------------------------------------------------
# 4. Ribbon boards
# ---------------------------------------------------------------------------
def build_ribbon() -> None:
    width, height = 4096, 256
    canvas = vgradient((width, height), (9, 26, 62), (4, 14, 36))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, width, 8], fill=LIONS_BLUE)
    draw.rectangle([0, height - 8, width, height], fill=LIONS_BLUE)
    phrases = ["WIN OR WOW", "혼연일체", "SAMSUNG LIONS", "WIN OR WOW", "VAMOS LIONS", "혼연일체"]
    x = 40
    for index, phrase in enumerate(phrases):
        body_font = BOLD if any("\uac00" <= ch <= "\ud7a3" for ch in phrase) else DISPLAY
        use = fit(draw, phrase, body_font, 120, 520)
        draw.text((x, height // 2), phrase, font=use, fill=WHITE if index % 2 == 0 else GOLD, anchor="lm")
        x += draw.textlength(phrase, font=use) + 90
        if x > width - 420:
            break
    canvas = led_grid(canvas, 4, 0.14)
    canvas.save(OUT / "brand-ribbon-winorwow.jpg", quality=93)


# ---------------------------------------------------------------------------
# 5. Mascot family: 블레오 · 핑크레오 · 레니 · 라온
# ---------------------------------------------------------------------------
def build_mascots() -> None:
    width, height = 2048, 1024
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    family = [
        ("블레오", "BLEO", LIONS_BLUE, (12, 42, 96), WHITE, "7", 320),
        ("핑크레오", "PINKLEO", PINK, (250, 196, 214), WHITE, "11", 780),
        ("레니", "RENI", SUN, (255, 232, 170), NAVY, "21", 1240),
        ("라온", "RAON", MINT, (198, 240, 232), NAVY, "33", 1700),
    ]
    for name, english, body, mane, jersey, number, cx in family:
        draw_lion(draw, cx, 416, 168, body, mane, jersey, number)
        text(draw, (cx, 792), name, BOLD, 84, NAVY, anchor="mm", stroke=1)
        text(draw, (cx, 862), english, DISPLAY, 54, (44, 76, 128), anchor="mm")
    canvas.save(OUT / "brand-mascots.png")


# ---------------------------------------------------------------------------
# 6. Cadastral plan board: 지적도 151,526.00 ㎡
# ---------------------------------------------------------------------------
def parcelled_octagon(radius: float, bevel: float, cx: float, cy: float):
    """Octagon whose surface area equals the official parcel: A = 2 (1+√2) a² - 4·bevel²/2."""
    pts = []
    for k in range(8):
        angle = math.pi / 4 * k + math.pi / 8
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return pts


def build_cadastre() -> None:
    width = height = 1600
    canvas = Image.new("RGB", (width, height), (244, 246, 244))
    draw = ImageDraw.Draw(canvas)
    for x in range(0, width, 50):
        draw.line([(x, 0), (x, height)], fill=(226, 230, 226))
    for y in range(0, height, 50):
        draw.line([(0, y), (width, y)], fill=(226, 230, 226))
    # parcel: regular octagon with area 151,526.00 m2  ->  a = sqrt(A / (2(1+sqrt2)))
    area = 151526.0
    a = math.sqrt(area / (2 * (1 + math.sqrt(2))))  # side length of a regular octagon
    r = a / (2 * math.sin(math.pi / 8))  # circumradius
    scale = 560.0 / r
    cx, cy = 800, 800
    pts = parcelled_octagon(r * scale, 0, cx, cy)
    draw.polygon(pts, fill=(226, 240, 228), outline=(26, 58, 40))
    draw.line(pts + [pts[0]], fill=(16, 40, 30), width=6)
    # hectare grid inside the parcel
    for gx in range(-600, 601, 50):
        draw.line([(cx + gx, cy - 620), (cx + gx, cy + 620)], fill=(208, 224, 208))
    for gy in range(-600, 601, 50):
        draw.line([(cx - 620, cy + gy), (cx + 620, cy + gy)], fill=(208, 224, 208))
    draw.polygon(pts, fill=None, outline=(16, 40, 30), width=6)
    # stadium footprint inside
    inner = parcelled_octagon(r * scale * 0.34, 0, cx, cy)
    draw.polygon(inner, fill=(206, 214, 224), outline=(40, 60, 90), width=3)
    text(draw, (cx, cy - 6), "야구장", BOLD, 44, (30, 50, 80), anchor="mm")
    text(draw, (cx, cy + 46), "STADIUM", DISPLAY, 30, (60, 80, 110), anchor="mm")
    # parcel area callout inside the plot
    text(draw, (cx, cy - 430), "대지면적  151,526.00 ㎡", BOLD, 46, (120, 40, 40), anchor="mm")
    text(draw, (cx, cy - 380), "PARCEL AREA  ·  151,526.00 m²", DISPLAY, 30, (140, 80, 70), anchor="mm")
    # north arrow
    draw.polygon([(1420, 150), (1396, 240), (1420, 216), (1444, 240)], fill=(30, 40, 60))
    text(draw, (1420, 268), "N", DISPLAY, 46, (30, 40, 60), anchor="mm")
    # scale bar
    draw.line([(120, 1460), (620, 1460)], fill=(30, 40, 60), width=5)
    for k in range(6):
        draw.line([(120 + k * 100, 1444), (120 + k * 100, 1476)], fill=(30, 40, 60), width=3)
    text(draw, (120, 1496), "0", BOLD, 28, (30, 40, 60), anchor="ma")
    text(draw, (620, 1496), "50 m", BOLD, 28, (30, 40, 60), anchor="ma")
    # title block
    draw.rectangle([60, 60, 900, 190], fill=(255, 255, 255), outline=(30, 40, 60), width=3)
    text(draw, (84, 96), "지적도  CADASTRAL PLAN", BOLD, 46, (20, 34, 60))
    text(draw, (84, 150), "대구광역시 수성구 야구전설로 1  ·  대구 삼성 라이온즈 파크", BOLD, 26, (60, 70, 90))
    draw.rectangle([60, 1300, 900, 1400], fill=(255, 255, 255), outline=(30, 40, 60), width=3)
    text(draw, (84, 1322), "대지면적  151,526.00 ㎡", BOLD, 34, (20, 34, 60))
    text(draw, (84, 1362), "좌·우 99.5 m  ·  좌중·우중 123.4 m  ·  중앙 122.5 m  ·  펜스 3.6 m", BOLD, 22, (60, 70, 90))
    canvas.save(OUT / "brand-cadastre-plan.png")


# ---------------------------------------------------------------------------
# 7. Forecourt welcome arch
# ---------------------------------------------------------------------------
def build_arch() -> None:
    width, height = 3072, 1024
    canvas = vgradient((width, height), (10, 30, 72), (4, 12, 30))
    glow, mask = radial((width, height), (1500, 500), 1400, (0, 86, 170), 1.0)
    canvas = Image.composite(glow, canvas, mask)
    draw = ImageDraw.Draw(canvas)
    text(draw, (150, 200), "WIN OR WOW", DISPLAY, 330, WHITE, width=1700)
    text(draw, (156, 560), "혼연일체  ·  대구 삼성 라이온즈 파크", BOLD, 96, GOLD, width=1700, stroke=2)
    text(draw, (156, 720), "오늘도 라팍에서  ·  WELCOME TO LIONS PARK", BOLD, 62, ICE, width=1700)
    family = [("블레오", LIONS_BLUE, (12, 42, 96)), ("핑크레오", PINK, (250, 196, 214))]
    for index, (name, body, mane) in enumerate(family):
        draw_lion(draw, 2280 + index * 380, 360, 150, body, mane, WHITE, "")
        text(draw, (2280 + index * 380, 700), name, BOLD, 58, ICE, anchor="mm")
    canvas = led_grid(canvas, 7, 0.12)
    canvas.save(OUT / "brand-forecourt-arch.jpg", quality=93)


def main() -> None:
    build_scoreboard()
    build_fence_murals()
    build_sponsors()
    build_ribbon()
    build_mascots()
    build_cadastre()
    build_arch()
    written = sorted(path.name for path in OUT.glob("brand-*"))
    print("wrote", len(written), "brand maps:")
    for name in written:
        size = (OUT / name).stat().st_size
        print(f"  {name:38s} {size / 1024:8.1f} KB")


if __name__ == "__main__":
    main()
