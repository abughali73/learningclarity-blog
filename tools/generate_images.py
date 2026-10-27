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
STYLE = ("Cinematic film still, as if from a high-end feature film: photorealistic, shot on a full-frame cinema "
         "camera with a 35mm or 50mm prime lens, shallow depth of field with soft bokeh, motivated natural light "
         "with deliberate contrast and gentle haze, rich but natural colour grading with warm highlights and teal "
         "shadows, subtle film grain, thoughtful composition with a clear focal point and real depth. Believable "
         "fictional people with natural, expressive faces and hands. Not a stock photo, not an illustration, not "
         "cartoonish, no oversaturation. Absolutely no text, letters, numbers, logos, watermarks or brand marks, "
         "no readable screens or app interfaces, and no real or recognisable people.")


LARGE_WIDTH, SMALL_WIDTH, SHARE_WIDTH = 1280, 640, 1200


def save_image(png, out, share=False):
    """Save a generated picture in fast-loading formats.

    For a .webp src: <name>.webp (1280 px wide) and <name>-640.webp for small screens and thumbnails.
    For the hero (share=True) also <name>.jpg (1200 px), because some social networks don't show WebP previews.
    Any other extension is written as delivered.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() != ".webp":
        out.write_bytes(png)
        return
    im = Image.open(io.BytesIO(png)).convert("RGB")

    def resized(width):
        return im if im.width <= width else im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)

    resized(LARGE_WIDTH).save(out, "WEBP", quality=78, method=6)
    resized(SMALL_WIDTH).save(out.with_name(out.stem + "-640.webp"), "WEBP", quality=75, method=6)
    if share:
        resized(SHARE_WIDTH).save(out.with_suffix(".jpg"), "JPEG", quality=82, optimize=True, progressive=True)


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
    todo = {}
    for path in sorted((ROOT / "_posts").glob("*/*.md")):
        fm = front_matter(path)
        hero = fm.get("hero_image") or {}
        for item in [hero] + list(fm.get("scenes") or []):
            src, prompt = item.get("src"), item.get("prompt")
            if src and prompt and src not in todo and not (ROOT / src.lstrip("/")).exists():
                todo[src] = (path, prompt, item is hero)
    if not todo:
        print("No images to generate.")
        return 0
    if not key:
        print(f"::error::{len(todo)} image(s) are waiting, but the OPENAI_API_KEY repository secret is missing "
              "or empty. Add it under Settings > Secrets and variables > Actions > Repository secrets.")
        return 1
    print(f"Generating {len(todo)} image(s) with {model}.")
    failed = 0
    for src, (path, prompt, is_hero) in todo.items():
        out = ROOT / src.lstrip("/")
        try:
            save_image(generate(prompt, key, model, size, quality), out, share=is_hero)
            print(f"{path.relative_to(ROOT)} -> {src}")
        except Exception as exc:  # keep going; report at the end
            failed += 1
            detail = exc.read().decode(errors="replace")[:500] if hasattr(exc, "read") else str(exc)
            print(f"::error::{src} ({path.relative_to(ROOT)}): {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
