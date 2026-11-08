"""Prepare the Lions Park v5 brand media textures from the supplied artwork.

The source files are the owner's own Samsung Lions victory graphics. They are
kept untouched under ``assets/graphics/`` and composited here into the LED wall,
ribbon board and banner textures the Blender build maps onto the park.

Run with a normal CPython that has Pillow installed:

    python3 scripts/prepare-v5-graphics.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "graphics"
OUT = ROOT / "assets" / "blender" / "textures"
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "victory-step": "a7984c9e-6a09-4c5c-9cf3-591d86dea7e5.png",
    "ks2026-08": "35166631-d2bc-44bc-9b1f-bcd39f81ef1f.png",
    "ks2026-05": "8342ed11-9041-4454-a90b-ba47cebe00a3.png",
    "ks2026-03": "df92ef8b-b82f-4dad-adf2-e6a5d71acb92.png",
    "qaed-02": "b86c58c3-27b9-4840-a05e-16ed94871526.png",
    "emblem-sl": "74833d67-5d1a-4289-8dab-5d17b07583dc.png",
}

NAVY = (9, 32, 74)
DEEP_NAVY = (5, 16, 40)
LED_NAVY = (7, 24, 56)


def load(name: str) -> Image.Image:
    return Image.open(SRC / SOURCES[name]).convert("RGBA")


def on_background(image: Image.Image, size, color) -> Image.Image:
    canvas = Image.new("RGB", size, color)
    scaled = image.copy()
    scaled.thumbnail(size, Image.LANCZOS)
    left = (size[0] - scaled.width) // 2
    top = (size[1] - scaled.height) // 2
    canvas.paste(scaled, (left, top), scaled)
    return canvas


def led_grid(canvas: Image.Image, cell: int = 5) -> Image.Image:
    """Fine LED cell grid plus a soft vignette, so the wall reads as an LED screen."""
    width, height = canvas.size
    grid = Image.new("RGB", canvas.size, (0, 0, 0))
    draw = ImageDraw.Draw(grid)
    for x in range(0, width, cell):
        draw.line([(x, 0), (x, height)], fill=(10, 10, 14))
    for y in range(0, height, cell):
        draw.line([(0, y), (width, y)], fill=(10, 10, 14))
    grid = grid.filter(ImageFilter.GaussianBlur(0.6))
    mixed = Image.blend(canvas, grid, 0.22)

    vignette = Image.new("L", canvas.size, 0)
    vdraw = ImageDraw.Draw(vignette)
    vdraw.ellipse(
        [(-width * 0.15, -height * 0.35), (width * 1.15, height * 1.35)], fill=255
    )
    vignette = vignette.filter(ImageFilter.GaussianBlur(width * 0.05))
    dark = Image.new("RGB", canvas.size, (0, 0, 0))
    return Image.composite(mixed, dark, vignette)


def _led_lettering(image: Image.Image, tint) -> Image.Image:
    """Turn an opaque artwork into emissive LED lettering for a dark screen."""
    grey = image.convert("L")
    alpha = grey.point(lambda value: max(0, min(255, int((225 - value) * 1.35))))
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.7))
    letters = Image.new("RGBA", image.size, (*tint, 0))
    letters.putalpha(alpha)
    return letters


def _led_base(width: int, height: int, deep: bool = False) -> Image.Image:
    canvas = Image.new("RGB", (width, height), (4, 10, 26) if deep else LED_NAVY)
    draw = ImageDraw.Draw(canvas)
    for y in range(height):
        t = y / height
        top = (4, 10, 26) if deep else (9, 28, 72)
        bottom = (2, 5, 14) if deep else (13, 44, 104)
        draw.line(
            [(0, y), (width, y)],
            fill=(
                int(top[0] + (bottom[0] - top[0]) * t),
                int(top[1] + (bottom[1] - top[1]) * t),
                int(top[2] + (bottom[2] - top[2]) * t),
            ),
        )
    return canvas


def scoreboard() -> None:
    """36 m x 20.4 m main LED: crest/victory lockup above the step slogan."""
    width, height = 2400, 1360
    crest = load("ks2026-08")
    base = crest.convert("RGB").getpixel((4, 4))
    canvas = _led_base(width, height)
    canvas = Image.new("RGB", (width, height), base)
    crest = crest.copy()
    crest = crest.resize((width, round(width * crest.height / crest.width)), Image.LANCZOS)
    canvas.paste(crest, (0, 0), crest)
    seam = crest.height
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, seam, width, height], fill=(6, 18, 44))
    draw.line([(0, seam), (width, seam)], fill=(96, 176, 255), width=5)
    draw.line([(0, height - 3), (width, height - 3)], fill=(96, 176, 255), width=5)

    step = load("victory-step")
    step.thumbnail((1500, height - seam - 40), Image.LANCZOS)
    slogan = _led_lettering(step, (226, 240, 255))
    canvas.paste(slogan, ((width - step.width) // 2, seam + 30), slogan)

    led_grid(canvas).save(OUT / "brand-scoreboard-victory.jpg", quality=93)


def scoreboard_night() -> None:
    """Same wall in the low-light victory look for night preview renders."""
    width, height = 2400, 1360
    crest = load("ks2026-08")
    canvas = Image.new("RGB", (width, height), crest.convert("RGB").getpixel((4, 4)))
    crest = crest.resize((width, round(width * crest.height / crest.width)), Image.LANCZOS)
    canvas.paste(crest, (0, 0), crest)
    seam = crest.height
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, seam, width, height], fill=(3, 9, 22))
    draw.line([(0, seam), (width, seam)], fill=(70, 130, 255), width=5)
    step = load("victory-step")
    step.thumbnail((1500, height - seam - 40), Image.LANCZOS)
    slogan = _led_lettering(step, (255, 222, 132))
    canvas.paste(slogan, ((width - step.width) // 2, seam + 30), slogan)
    led_grid(canvas).save(OUT / "brand-scoreboard-victory-night.jpg", quality=93)


def ribbon() -> None:
    for name, key, color in [
        ("brand-ribbon-ks", "ks2026-03", NAVY),
        ("brand-ribbon-samsung", "ks2026-05", DEEP_NAVY),
    ]:
        image = load(key)
        canvas = on_background(image, (2048, 512), color)
        canvas.save(OUT / f"{name}.jpg", quality=93)


def banners() -> None:
    on_background(load("qaed-02"), (2048, 922), NAVY).save(
        OUT / "brand-banner-qaed.jpg", quality=93
    )
    emblem = load("emblem-sl")
    emblem.thumbnail((1024, 1024), Image.LANCZOS)
    flat = Image.new("RGB", emblem.size, (16, 32, 78))
    flat.paste(emblem, (0, 0), emblem)
    flat.save(OUT / "brand-emblem-sl.jpg", quality=93)


def manifest() -> None:
    record = {
        "sources": {name: f"assets/graphics/{file}" for name, file in SOURCES.items()},
        "outputs": sorted(path.name for path in OUT.glob("brand-*")),
        "note": "Owner-supplied Samsung Lions victory graphics, composited for LED mapping.",
    }
    (ROOT / "assets" / "graphics" / "manifest.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    scoreboard()
    scoreboard_night()
    ribbon()
    banners()
    manifest()
    for path in sorted(OUT.glob("brand-*")):
        print(f"{path.name:38s} {path.stat().st_size / 1024:8.1f} KB")
