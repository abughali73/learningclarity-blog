#!/usr/bin/env python3
"""Generate AI images (the hero image and the in-post `scenes:`) for posts with the OpenAI Images API.

Runs in GitHub Actions (.github/workflows/generate-images.yml), never in the blog agent's sandbox.
A post asks for an illustration with this front matter:

  hero_image:
    src: /assets/img/posts/<slug>-hero.png
    alt: "Short description of the picture"
    prompt: "What to draw. No text, no logos, no real people."

For every hero_image.src that does not exist yet, the image is generated once and saved there
(the five language versions of a post share one src, so they share one image).
The post layout shows the picture only once the file exists, so a post never shows a broken image.

Environment:
  OPENAI_API_KEY      (repository secret, required)
  OPENAI_IMAGE_MODEL  (repository variable, optional: the exact model ID, default gpt-image-2.5-flare)
  OPENAI_IMAGE_SIZE   (optional, default 1536x1024)
  OPENAI_IMAGE_QUALITY (optional, default high)
  IMAGE_RESTYLE_LIMIT (optional, default 0: how many older-style images to redo per run)
  IMAGE_ONLY          (optional: regenerate just this one src, for testing a style)
"""
import base64
import io
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "gpt-image-2.5-flare"
# Bump STYLE_VERSION whenever STYLE changes: every image made with an older version is regenerated
# (in place, so the old picture stays live until the new one is committed). The version of each
# image is recorded in assets/img/posts/styles.json.
STYLE_VERSION = 2
STYLE = ("Bright, inspirational and tech-savvy photorealistic image, like a premium technology brand campaign. "
         "Clean, modern, light-filled spaces (glass walls, warm wood, plants, daylight from large windows) with "
         "cool blue accent lighting. Where it fits the moment, a softly glowing, translucent holographic panel floats "
         "near the person, showing abstract learning visuals: node diagrams, mind-map branches, flowing charts, "
         "waveforms or simple icons, in luminous blue and white, as if the person's study material is coming to "
         "life around them. The person looks focused, capable and optimistic. High-key, crisp and sharp, vibrant but "
         "natural colours with blue and white highlights, gentle shallow depth of field, realistic skin and hands. "
         "Even evening or night scenes stay bright and well lit with a hopeful mood; never gloomy, grey or murky. "
         "Not an illustration, not cartoonish, not a generic stock photo. Absolutely no legible text, letters, "
         "numbers, logos, watermarks or brand marks anywhere (holographic panels show only abstract shapes and "
         "glyph-free diagrams; no logos on laptops, mugs, lanyards or clothing), and no real or recognisable people.")


LARGE_WIDTH, SMALL_WIDTH, SHARE_WIDTH = 1280, 640, 1200
AVIF_QUALITY, WEBP_QUALITY = 50, 75
MANIFEST = ROOT / "assets/img/posts/styles.json"


def save_image(png, out, share=False):
    """Save a generated picture in the lightest formats browsers load.

    For a .webp src, each picture is saved 1280 px and 640 px wide as:
      <name>.avif / <name>-640.avif  (AVIF: smallest files; the layouts offer these first)
      <name>.webp / <name>-640.webp  (WebP fallback for the few browsers without AVIF)
    and for the hero (share=True) also <name>.jpg (1200 px), because social networks don't show AVIF/WebP previews.
    Any other extension is written as delivered.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() != ".webp":
        out.write_bytes(png)
        return
    im = Image.open(io.BytesIO(png)).convert("RGB")

    def resized(width):
        return im if im.width <= width else im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)

    large, small = resized(LARGE_WIDTH), resized(SMALL_WIDTH)
    large.save(out.with_suffix(".avif"), "AVIF", quality=AVIF_QUALITY, speed=4)
    small.save(out.with_name(out.stem + "-640.avif"), "AVIF", quality=AVIF_QUALITY, speed=4)
    large.save(out, "WEBP", quality=WEBP_QUALITY, method=6)
    small.save(out.with_name(out.stem + "-640.webp"), "WEBP", quality=WEBP_QUALITY, method=6)
    if share:
        resized(SHARE_WIDTH).save(out.with_suffix(".jpg"), "JPEG", quality=80, optimize=True, progressive=True)


def front_matter(path):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", path.read_text(encoding="utf-8"), re.S)
    return yaml.safe_load(m.group(1)) if m else {}


def generate(prompt, key, model, size, quality):
    body = {"model": model, "prompt": f"{prompt}\n\n{STYLE}", "size": size, "n": 1}
    if quality:
        body["quality"] = quality
    req = urllib.request.Request("https://api.openai.com/v1/images/generations",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)["data"][0]
    if data.get("b64_json"):
        return base64.b64decode(data["b64_json"])
    with urllib.request.urlopen(data["url"], timeout=120) as r:
        return r.read()


def main():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_IMAGE_MODEL", "").strip() or DEFAULT_MODEL
    size = os.environ.get("OPENAI_IMAGE_SIZE", "").strip() or "1536x1024"
    quality = os.environ.get("OPENAI_IMAGE_QUALITY", "").strip() or "high"
    # Missing images are always made; restyling older images is capped per run so a run stays well
    # inside the Actions time limit (the hourly schedule picks up the rest).
    limit = int(os.environ.get("IMAGE_RESTYLE_LIMIT", "").strip() or 0)  # 0 until the new style is approved
    only = os.environ.get("IMAGE_ONLY", "").strip()
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    missing, restyle = {}, {}
    # Newest posts first, and heroes before scenes, so the most visible pictures change first.
    for path in sorted((ROOT / "_posts").glob("*/*.md"), key=lambda p: p.name, reverse=True):
        fm = front_matter(path)
        hero = fm.get("hero_image") or {}
        for item in [hero] + list(fm.get("scenes") or []):
            src, prompt = item.get("src"), item.get("prompt")
            if not (src and prompt) or src in missing or src in restyle:
                continue
            if only and src != only:
                continue
            if not (ROOT / src.lstrip("/")).exists():
                missing[src] = (path, prompt, item is hero)
            elif manifest.get(src) != STYLE_VERSION:
                restyle[src] = (path, prompt, item is hero)
    restyle = dict(sorted(restyle.items(), key=lambda kv: not kv[1][2]))
    todo = {**missing, **dict(list(restyle.items())[:limit])}
    if not todo:
        print("No images to generate.")
        return 0
    if not key:
        print(f"::error::{len(todo)} image(s) are waiting, but the OPENAI_API_KEY repository secret is missing "
              "or empty. Add it under Settings > Secrets and variables > Actions > Repository secrets.")
        return 1
    print(f"Generating {len(missing)} missing and {len(todo) - len(missing)} of {len(restyle)} restyled image(s) "
          f"with {model} (style v{STYLE_VERSION}).")
    failed = 0
    for src, (path, prompt, is_hero) in todo.items():
        out = ROOT / src.lstrip("/")
        try:
            save_image(generate(prompt, key, model, size, quality), out, share=is_hero)
            manifest[src] = STYLE_VERSION
            MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
            print(f"{path.relative_to(ROOT)} -> {src}")
        except Exception as exc:  # keep going; report at the end
            failed += 1
            detail = exc.read().decode(errors="replace")[:500] if hasattr(exc, "read") else str(exc)
            print(f"::error::{src} ({path.relative_to(ROOT)}): {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
