#!/usr/bin/env python3
"""Generate the per-language narration tracks of feature-update clips with Gemini TTS.

Runs in GitHub Actions (.github/workflows/generate-narration.yml), never in an agent's sandbox.
A feature-update post asks for narration with one file per post, `_narration/<ref>.yml`:

  ref: <the post's ref>
  voice: Zephyr                      # a Gemini prebuilt voice (female, bright)
  style:                             # delivery instructions per language (speech_metadata style)
    en: "Warm, excited and inspirational, ..."
    ar: "Egyptian Arabic with a Cairo accent, ..."
  clips:
    - id: saved-lessons              # the feature id; the clip is assets/video/features/<ref>/<id>.mp4
      text:
        en: "..."
        ar: "..."                    # written in Egyptian Arabic for a Cairo accent
        es: "..."
        fr: "..."
        de: "..."

For every clip and language whose assets/video/features/<ref>/<id>-<lang>.m4a does not exist yet, the text is
spoken once and saved as AAC (mono, 64 kbps, loudness-normalised). The post shows "Play with narration" for a
language once its file exists.

Environment:
  GEMINI_API_KEY      (repository secret, required; without it nothing is generated)
  GEMINI_TTS_MODEL    (optional, default gemini-3.8-flash-tts)
  NARRATION_ONLY      (optional: regenerate just this ref)
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LANGS = ["en", "ar", "es", "fr", "de"]
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"


def find_audio(obj):
    """The last base64 audio block anywhere in the response."""
    found = None
    if isinstance(obj, dict):
        if obj.get("type") == "audio" and isinstance(obj.get("data"), str):
            found = obj["data"]
        for v in obj.values():
            found = find_audio(v) or found
    elif isinstance(obj, list):
        for v in obj:
            found = find_audio(v) or found
    return found


def speak(key, model, voice, text, style):
    part = {"type": "text", "text": text}
    if style:
        part["annotations"] = [{"type": "speech_metadata", "style": style}]
    body = {
        "model": model,
        "input": [{"type": "user_input", "content": [part]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]},
    }
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), method="POST",
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = find_audio(json.load(r))
            if not data:
                raise RuntimeError("no audio in the response")
            return base64.b64decode(data)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:400]
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(attempt * 15)
                continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")
    raise RuntimeError("gave up after retries")


def to_m4a(wav_bytes, out):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        src = f.name
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ac", "1", "-ar", "24000", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(out)],
                   check=True)
    os.unlink(src)


def main():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_TTS_MODEL", "").strip() or "gemini-3.8-flash-tts"
    only = os.environ.get("NARRATION_ONLY", "").strip()
    todo = []
    for spec_path in sorted((ROOT / "_narration").glob("*.yml")):
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        ref = spec.get("ref") or spec_path.stem
        if only and ref != only:
            continue
        for clip in spec.get("clips") or []:
            for lang in LANGS:
                text = (clip.get("text") or {}).get(lang)
                out = ROOT / "assets" / "video" / "features" / ref / f"{clip['id']}-{lang}.m4a"
                if text and (not out.exists() or only):
                    todo.append((spec.get("voice") or "Zephyr", (spec.get("style") or {}).get(lang, ""), text, out))
    if not todo:
        print("No narration to generate.")
        return 0
    if not key:
        print(f"::warning::GEMINI_API_KEY is not set; {len(todo)} narration track(s) are waiting.")
        return 0
    failed = 0
    for voice, style, text, out in todo:
        try:
            to_m4a(speak(key, model, voice, text.strip(), style), out)
            print(f"made {out.relative_to(ROOT)}")
        except Exception as exc:  # keep going; report at the end
            failed += 1
            print(f"::error::{out.relative_to(ROOT)}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
