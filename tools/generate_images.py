#!/usr/bin/env python3
"""Generate AI illustrations for posts with the OpenAI Images API.

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
  OPENAI_IMAGE_QUALITY (optional, e.g. medium; omitted when empty)
"""
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "gpt-image-2.5-flare"
STYLE = ("Clean, friendly flat illustration for an education technology blog. Soft blue, purple and pink "
         "palette on a light background, simple shapes, plenty of white space. Absolutely no text, letters, "
         "numbers, logos, watermarks or brand marks, and no real or recognisable people.")


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
    quality = os.environ.get("OPENAI_IMAGE_QUALITY", "").strip()
    todo = {}
    for path in sorted((ROOT / "_posts").glob("*/*.md")):
        hero = front_matter(path).get("hero_image") or {}
        src, prompt = hero.get("src"), hero.get("prompt")
        if src and prompt and src not in todo and not (ROOT / src.lstrip("/")).exists():
            todo[src] = (path, prompt)
    if not todo:
        print("No images to generate.")
        return 0
    if not key:
        print("::warning::Set the OPENAI_API_KEY repository secret to generate images.")
        return 0
    print(f"Generating {len(todo)} image(s) with {model}.")
    failed = 0
    for src, (path, prompt) in todo.items():
        out = ROOT / src.lstrip("/")
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(generate(prompt, key, model, size, quality))
            print(f"{path.relative_to(ROOT)} -> {src}")
        except Exception as exc:  # keep going; report at the end
            failed += 1
            detail = exc.read().decode(errors="replace")[:500] if hasattr(exc, "read") else str(exc)
            print(f"::error::{src} ({path.relative_to(ROOT)}): {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
