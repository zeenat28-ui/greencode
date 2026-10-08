#!/usr/bin/env python3
"""Generate the Alexa+ store media assets in alexa/assets/.

    python scripts/gen_alexa_icons.py

Produces every size the addon.json schema asks for (64, 72, 88, 126, 180,
241 px) in light and dark variants plus the 600x900 carousel image, so the
manifest references real files instead of placeholder hosts. The glyphs are
drawn, not font-dependent at small sizes: two overlapping discs form the
leaf lens, a stem line grounds it.
"""
import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alexa", "assets")

GREEN = (11, 122, 75)        # brand green - light-mode tile
GREEN_DARK = (6, 59, 39)     # dark-mode tile
LEAF_LIGHT = (235, 250, 242)
LEAF_DARK = (72, 214, 145)
INK = (22, 48, 42)

ICON_SIZES = [64, 72, 88, 126, 180, 241]


def leaf_mask(size):
    """Mask of an upright leaf: the lens where two side-offset discs overlap,
    rotated slightly, with a stem drawn from its bottom tip."""
    from PIL import ImageChops

    r = int(size * 0.30)
    off = int(size * 0.14)
    cx, cy = size // 2, size // 2 + int(size * 0.03)

    a = Image.new("L", (size, size), 0)
    b = Image.new("L", (size, size), 0)
    ImageDraw.Draw(a).ellipse([cx + off - r, cy - r, cx + off + r, cy + r], fill=255)
    ImageDraw.Draw(b).ellipse([cx - off - r, cy - r, cx - off + r, cy + r], fill=255)
    lens = ImageChops.multiply(a, b)  # intersection, not union

    half_h = int((r * r - off * off) ** 0.5)  # lens tip distance from centre
    d = ImageDraw.Draw(lens)
    w = max(2, size // 26)
    d.line(
        [(cx, cy + half_h - w), (cx - int(size * 0.10), size - int(size * 0.12))],
        fill=255,
        width=w,
    )
    # Vein down the middle, then a slight tilt so it reads as a leaf.
    d.line([(cx, cy - half_h + w), (cx, cy + half_h - w)], fill=140, width=max(1, w // 2))
    return lens.rotate(-20, resample=Image.BICUBIC, center=(cx, cy))


def make_icon(size, bg, leaf, radius_ratio=0.22):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tile = Image.new("RGBA", (size, size), bg + (255,))
    # Rounded corners by masking a plain rectangle.
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=max(4, int(size * radius_ratio)), fill=255
    )
    img.paste(tile, (0, 0), mask)

    mask = leaf_mask(size)
    glyph = Image.new("RGBA", (size, size), leaf + (0,))
    solid = Image.new("RGBA", (size, size), leaf + (255,))
    glyph = Image.composite(solid, glyph, mask)
    img.alpha_composite(glyph)
    return img


def _font(size):
    for name in ("arialbd.ttf", "arial.ttf"):
        path = os.path.join("C:\\Windows\\Fonts", name)
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_carousel():
    w, h = 600, 900
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    # Vertical brand gradient.
    top, bottom = (6, 59, 39), (11, 122, 75)
    for y in range(h):
        t = y / h
        d.line(
            [(0, y), (w, y)],
            fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)),
        )
    d.text((48, 56), "GreenCode", font=_font(56), fill=LEAF_LIGHT)
    d.text((48, 124), "AI code audits for energy & carbon",
           font=_font(24), fill=(178, 224, 204))

    # Faux audit-result card.
    card = [48, 200, w - 48, 560]
    d.rounded_rectangle(card, radius=24, fill=(245, 251, 248))
    d.text((80, 240), "audit_and_score", font=_font(26), fill=(107, 122, 117))
    d.text((80, 286), "Score 77 / 100", font=_font(44), fill=INK)
    d.text((80, 346), "Grade C", font=_font(30), fill=(180, 120, 0))
    d.text((80, 404), "1. quadratic string build   -31%", font=_font(22), fill=INK)
    d.text((80, 440), "2. nested loop over rows    -18%", font=_font(22), fill=INK)
    d.text((80, 476), "3. duplicate log alloc      -12%", font=_font(22), fill=INK)
    d.text((80, 512), "plan: 3 steps, measured + modelled", font=_font(20), fill=(107, 122, 117))

    # Regional comparison strip.
    d.rounded_rectangle([48, 596, w - 48, 792], radius=24, fill=(235, 250, 242))
    d.text((80, 628), "compare_regions", font=_font(26), fill=(107, 122, 117))
    for i, (zone, val) in enumerate((("IE", "286"), ("US-VA", "343"), ("FR", "50"))):
        y = 676 + i * 38
        d.text((80, y), zone, font=_font(24), fill=INK)
        bar = int(300 * int(val) / 400)
        d.rectangle([200, y + 4, 200 + bar, y + 22], fill=GREEN)
        d.text((516, y), val, font=_font(20), fill=(107, 122, 117))

    d.text((48, 836), "MCP · self-hosted · sub-500 ms", font=_font(22), fill=(178, 224, 204))
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    for size in ICON_SIZES:
        make_icon(size, GREEN, LEAF_LIGHT).save(
            os.path.join(OUT, f"icon-{size}x{size}.png")
        )
        make_icon(size, GREEN_DARK, LEAF_DARK).save(
            os.path.join(OUT, f"icon-dark-{size}x{size}.png")
        )
    make_carousel().save(os.path.join(OUT, "carousel-600x900.png"))
    print(f"wrote {2 * len(ICON_SIZES)} icons + carousel to {OUT}")


if __name__ == "__main__":
    main()
