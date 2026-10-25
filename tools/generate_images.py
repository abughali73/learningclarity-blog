#!/usr/bin/env python3
"""Generate AI illustrations for posts with the Google Gemini API.

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
  OPENAI_API_KEY       (repository secret, required: the Gemini API key)
  OPENAI_IMAGE_MODEL   (repository variable, optional: the Gemini model, default gemini-flash-latest)
  GEMINI_ASPECT_RATIO  (repository variable, optional, default 3:2)
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

ROOT = Path(__file__).resolve().parent.parent
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-flash-latest"
STYLE = ("Clean, friendly flat illustration for an education technology blog. Soft blue, purple and pink "
         "palette on a light background, simple shapes, plenty of white space. Absolutely no text, letters, "
         "numbers, logos, watermarks or brand marks, and no real or recognisable people.")


def front_matter(path):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", path.read_text(encoding="utf-8"), re.S)
    return yaml.safe_load(m.group(1)) if m else {}


def to_png(data, mime):
    if mime == "image/png":
        return data
    from PIL import Image  # installed by the workflow
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).save(buf, format="PNG")
    return buf.getvalue()


def generate(prompt, key, model, aspect):
    body = {
        "contents": [{"parts": [{"text": f"Generate an image. {prompt}\n\n{STYLE}"}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": aspect}},
    }
    req = urllib.request.Request(API.format(model=model), data=json.dumps(body).encode(),
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        resp = json.load(r)
    texts = []
    for cand in resp.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                return to_png(base64.b64decode(inline["data"]), mime)
            if part.get("text"):
                texts.append(part["text"])
    reason = (resp.get("candidates") or [{}])[0].get("finishReason") or resp.get("promptFeedback")
    raise RuntimeError(f"Model {model} returned no image (finish reason: {reason}). "
                       f"Text returned: {' '.join(texts)[:300] or 'none'}. "
                       "If this model cannot output images, set the OPENAI_IMAGE_MODEL variable to an image model.")


def main():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_IMAGE_MODEL", "").strip() or DEFAULT_MODEL
    aspect = os.environ.get("GEMINI_ASPECT_RATIO", "").strip() or "3:2"
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
        print("::warning::Set the OPENAI_API_KEY repository secret (Gemini API key) to generate images.")
        return 0
    print(f"Generating {len(todo)} image(s) with {model}.")
    failed = 0
    for src, (path, prompt) in todo.items():
        out = ROOT / src.lstrip("/")
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(generate(prompt, key, model, aspect))
            print(f"{path.relative_to(ROOT)} -> {src}")
        except Exception as exc:  # keep going; report at the end
            failed += 1
            detail = exc.read().decode(errors="replace")[:500] if hasattr(exc, "read") else str(exc)
            print(f"::error::{src} ({path.relative_to(ROOT)}): {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
