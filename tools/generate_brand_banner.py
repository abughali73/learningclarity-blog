#!/usr/bin/env python3
"""Regenerate the blog's channel banner (assets/img/og-default.png, 1200x630): the default share image used by
every page without its own picture, and the banner for the blog's social channels.

The artwork is made with the OpenAI image model (same model as the post images, default gpt-image-2.5-flare);
the logo and the words are drawn on top here, so the logo is always the exact brand file
(assets/img/brand/lc-logo.png, from lc-logo.svg) and the text is always spelt correctly.

Runs in GitHub Actions (.github/workflows/generate-brand-banner.yml). Locally, pass --background <image> to test
the composition without calling the API.
"""
import argparse
import base64
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
LOGO = ROOT / "assets" / "img" / "brand" / "lc-logo.png"
OUT = ROOT / "assets" / "img" / "og-default.png"
W, H = 1200, 630
NAVY, NAVY_2, GOLD, GOLD_2, INK, MUTED = (27, 52, 128), (20, 40, 104), (226, 160, 36), (209, 142, 20), (15, 23, 42), (71, 85, 105)

PROMPT = (
    "Wide banner artwork for an AI-powered study platform. A bright, airy, modern learning space filled with soft "
    "morning daylight: on the RIGHT half, a sleek desk with an open laptop seen from the side (screen not visible), "
    "an open notebook and a few books, and above them gentle translucent holographic learning visuals - floating "
    "glowing cards, connected nodes and a soft brain-like constellation - in deep navy blue and warm golden amber "
    "light. The LEFT 55% of the image is calm, clean, almost empty soft white-to-pale-cream space with only a very "
    "faint navy and gold light haze, reserved for a logo and text that will be added later. Colour palette: white, "
    "deep navy blue (#1B3480) and warm gold (#E2A024). Optimistic, premium, tech-savvy, photographic quality with "
    "shallow depth of field. No people, no text, no letters, no numbers, no logos, no watermarks, no screens with "
    "readable content."
)


def openai_art(key, model, quality):
    body = {"model": model, "prompt": PROMPT, "size": "1536x1024", "n": 1}
    if quality:
        body["quality"] = quality
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.load(r)["data"][0]
    raw = base64.b64decode(data["b64_json"]) if data.get("b64_json") else urllib.request.urlopen(data["url"]).read()
    return Image.open(io.BytesIO(raw)).convert("RGB")


def cover(im, size):
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    left = (im.width - tw) // 2
    top = (im.height - th) // 2
    return im.crop((left, top, left + tw, top + th))


def font(name, size):
    for d in (os.environ.get("BANNER_FONT_DIR", ""), str(ROOT / ".fonts"), "/usr/share/fonts/truetype/dejavu"):
        p = Path(d) / name
        if d and p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.truetype("DejaVuSans-Bold.ttf", size)


def compose(art):
    base = cover(art, (W, H)).convert("RGBA")
    # A soft white veil over the left side so the logo and words always read clearly.
    veil = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(veil)
    for x in range(W):
        a = 240 if x < 660 else max(0, int(240 * (1 - (x - 660) / 260)))
        vd.line([(x, 0), (x, H)], fill=a)
    base = Image.composite(Image.new("RGBA", (W, H), (255, 255, 255, 255)), base, veil)

    logo = Image.open(LOGO).convert("RGBA")
    lh = 150
    logo = logo.resize((round(logo.width * lh / logo.height), lh), Image.LANCZOS)
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sh = Image.new("RGBA", logo.size, (20, 40, 104, 70))
    shadow.paste(sh, (82, 96), logo)
    base = Image.alpha_composite(base, shadow.filter(ImageFilter.GaussianBlur(10)))
    base.alpha_composite(logo, (78, 88))

    d = ImageDraw.Draw(base)
    x = 78 + logo.width + 30
    f_brand = font("Poppins-Bold.ttf", 62)
    d.text((x, 104), "Learning", font=f_brand, fill=NAVY)
    d.text((x + d.textlength("Learning ", font=f_brand), 104), "Clarity", font=f_brand, fill=GOLD_2)
    d.text((x + 2, 186), "Clarity in Learning. Success in Every Step.", font=font("Poppins-Medium.ttf", 23), fill=MUTED)

    d.text((80, 318), "The LearningClarity Blog", font=font("Poppins-Bold.ttf", 44), fill=INK)
    body = font("Poppins-Medium.ttf", 27)
    d.text((80, 384), "AI tutoring, quizzes, exams and podcasts", font=body, fill=MUTED)
    d.text((80, 422), "in your language. Web, iPhone and Android.", font=body, fill=MUTED)
    d.text((80, 512), "blog.learningclarity.ai", font=font("Poppins-SemiBold.ttf", 28), fill=NAVY)

    bar = Image.new("RGBA", (W, 12))
    bd = ImageDraw.Draw(bar)
    for i in range(W):  # navy, a short blend, then gold (a straight RGB blend would turn grey in the middle)
        t = min(1, max(0, (i - 660) / 120))
        bd.line([(i, 0), (i, 12)], fill=tuple(round(NAVY[k] + (GOLD[k] - NAVY[k]) * t) for k in range(3)) + (255,))
    base.alpha_composite(bar, (0, H - 12))
    return base.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--background", help="test with this image instead of calling the API")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    if args.background:
        art = Image.open(args.background).convert("RGB")
    else:
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            print("::error::OPENAI_API_KEY is not set.")
            return 1
        model = os.environ.get("OPENAI_IMAGE_MODEL", "").strip() or "gpt-image-2.5-flare"
        art = openai_art(key, model, os.environ.get("OPENAI_IMAGE_QUALITY", "").strip() or "high")
        art.save(ROOT / "assets" / "img" / "brand" / "banner-art.jpg", "JPEG", quality=88)
        print(f"Artwork made with {model}.")
    compose(art).save(args.out, "PNG", optimize=True)
    print(f"Saved {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
