#!/usr/bin/env python3
"""Correct existing images with the OpenAI image edit API.

Runs in GitHub Actions (.github/workflows/edit-images.yml), never in the blog agent's sandbox.
Each entry in tools/image_edits.yml names a source image (tools/edit-src/...), the output src under
/assets/img/posts/ and an edit prompt. An entry is processed once: when its output already exists it is skipped.
Outputs are saved like generated heroes (WebP 1280 + 640, plus a JPEG for social previews).

Environment: OPENAI_API_KEY (secret), OPENAI_IMAGE_MODEL (variable, optional), OPENAI_IMAGE_QUALITY (optional).
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_images import DEFAULT_MODEL, save_image  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def multipart(fields, files):
    boundary = uuid.uuid4().hex
    out = bytearray()
    for name, value in fields.items():
        out += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
    for name, (filename, data, ctype) in files.items():
        out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\n"
                f"Content-Type: {ctype}\r\n\r\n").encode() + data + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def edit(image_path, prompt, key, model, quality, fidelity=True):
    fields = {"model": model, "prompt": prompt, "n": "1", "size": "1536x1024"}
    if quality:
        fields["quality"] = quality
    if fidelity:
        fields["input_fidelity"] = "high"
    body, ctype = multipart(fields, {"image[]": (image_path.name, image_path.read_bytes(), "image/png")})
    req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.load(r)["data"][0]
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        if fidelity and exc.code == 400 and "input_fidelity" in detail:
            return edit(image_path, prompt, key, model, quality, fidelity=False)
        raise RuntimeError(f"HTTP {exc.code}: {detail[:500]}") from None
    if data.get("b64_json"):
        return base64.b64decode(data["b64_json"])
    with urllib.request.urlopen(data["url"], timeout=120) as r:
        return r.read()


def main():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_IMAGE_MODEL", "").strip() or DEFAULT_MODEL
    quality = os.environ.get("OPENAI_IMAGE_QUALITY", "").strip() or "high"
    entries = yaml.safe_load((ROOT / "tools" / "image_edits.yml").read_text(encoding="utf-8")) or []
    todo = [e for e in entries if not (ROOT / e["output"].lstrip("/")).exists()]
    if not todo:
        print("No image edits waiting.")
        return 0
    if not key:
        print("::error::OPENAI_API_KEY is missing.")
        return 1
    failed = 0
    for e in todo:
        try:
            png = edit(ROOT / e["source"], e["prompt"], key, model, quality)
            save_image(png, ROOT / e["output"].lstrip("/"), share=True)
            print(f"{e['source']} -> {e['output']}")
        except Exception as exc:
            failed += 1
            print(f"::error::{e['output']}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
