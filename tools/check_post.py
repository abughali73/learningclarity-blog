#!/usr/bin/env python3
"""Check one post in all five languages before publishing.

Usage:
  python3 tools/check_post.py 2026-10-29-my-slug.md

Checks the front matter and body rules in AGENT.md (steps 5, 5b, 6 and 7) and exits with code 1 on any problem.
"""
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LANGS = ["en", "ar", "es", "fr", "de"]
ICONS = set("upload pencil hierarchy route bulb diagram question check headphones mic people bell clipboard chat "
            "clock award globe translate swap mail user-plus chart gift list dollar share flame star device layers "
            "target".split())
SHARED = ["ref", "capability", "image"]


def load(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("no front matter")
    return yaml.safe_load(m.group(1)), m.group(2)


def main(name):
    problems = []
    posts = {}
    for lang in LANGS:
        path = ROOT / "_posts" / lang / name
        if not path.exists():
            problems.append(f"{lang}: file missing ({path.relative_to(ROOT)})")
            continue
        try:
            posts[lang] = load(path)
        except Exception as exc:  # report every language, not just the first
            problems.append(f"{lang}: front matter does not parse: {exc}")
    for lang, (fm, body) in posts.items():
        p = lambda msg: problems.append(f"{lang}: {msg}")
        if fm.get("lang") != lang:
            p(f"lang is {fm.get('lang')!r}")
        if not 50 <= len(fm.get("title", "")) <= 65:
            p(f"title is {len(fm.get('title', ''))} characters (50 to 65)")
        if not 140 <= len(fm.get("description", "")) <= 160:
            p(f"description is {len(fm.get('description', ''))} characters (140 to 160)")
        if "author" in fm:
            p("remove the author: field")
        try:
            date = datetime.strptime(str(fm.get("date")), "%Y-%m-%d %H:%M:%S %z")
            if date > datetime.now(date.tzinfo):
                p("date is in the future")
        except ValueError:
            p(f"date {fm.get('date')!r} is not 'YYYY-MM-DD HH:MM:SS +ZZZZ'")
        tags = fm.get("tags") or []
        if not 10 <= len(tags) <= 15 or len(set(tags)) != len(tags) or any(" " in t or "#" in t for t in tags):
            p("tags: need 10 to 15 unique tags without spaces or #")
        if not fm.get("keywords"):
            p("keywords missing")
        ad = fm.get("ad") or {}
        items = ad.get("items") or []
        if len(items) != 4:
            p("ad.items needs exactly 4 items")
        for item in items:
            if item.get("icon") not in ICONS:
                p(f"ad icon {item.get('icon')!r} is not allowed")
            bullets = item.get("bullets") or []
            if len(bullets) != 2 or any(len(b) >= 60 for b in bullets):
                p(f"ad item {item.get('title')!r}: needs 2 bullets under 60 characters")
        if ad.get("color") not in ("blue", "purple", "pink", "orange"):
            p("ad.color must be blue, purple, pink or orange")
        for f in fm.get("faq") or []:
            if not f.get("q") or not f.get("a"):
                p("each faq item needs q and a")
        hero = fm.get("hero_image") or {}
        if not (hero.get("src") and hero.get("alt") and hero.get("prompt")):
            p("hero_image needs src, alt and prompt")
        if fm.get("image") != hero.get("src"):
            p("image must equal hero_image.src")
        scenes = fm.get("scenes") or []
        if not 4 <= len(scenes) <= 7:
            p(f"{len(scenes)} scenes (need 4 to 7)")
        for i, s in enumerate(scenes, 1):
            if not all(s.get(k) for k in ("src", "alt", "caption", "prompt")):
                p(f"scene {i} needs src, alt, caption and prompt")
            n = body.count("{% include scene.html n=" + str(i) + " %}")
            if n != 1:
                p(f"scene {i} is included {n} times in the body (need exactly 1)")
        if re.search(r"\{% include scene\.html n=(\d+) %\}", body) and \
                max(int(x) for x in re.findall(r"\{% include scene\.html n=(\d+) %\}", body)) > len(scenes):
            p("the body includes a scene number that is not in scenes:")
        if re.search(r"<img|!\[", body):
            p("the body contains an image; use scenes instead")
        for src in [hero.get("src")] + [s.get("src") for s in scenes]:
            if src and not src.startswith("/assets/img/posts/"):
                p(f"{src} must be under /assets/img/posts/")
    # values shared by all five languages
    if len(posts) == len(LANGS):
        def shared(fm):
            hero = fm.get("hero_image") or {}
            return ([fm.get(k) for k in SHARED] + [fm.get("ad", {}).get("color")]
                    + [i.get("icon") for i in fm.get("ad", {}).get("items") or []]
                    + [hero.get("src"), hero.get("prompt")]
                    + [(s.get("src"), s.get("prompt")) for s in fm.get("scenes") or []])
        values = {lang: shared(fm) for lang, (fm, _) in posts.items()}
        for lang in LANGS[1:]:
            if values[lang] != values["en"]:
                problems.append(f"{lang}: ref, capability, image, ad colour/icons or image src/prompt differ from en")
    # nothing under assets/img may be added by the agent
    staged = subprocess.run(["git", "status", "--porcelain", "--", "assets/img"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    if staged:
        problems.append("files changed under assets/img; the image workflow creates those, don't commit them:\n" + staged)
    if problems:
        print("Problems:\n- " + "\n- ".join(problems))
        return 1
    print(f"OK: {name} passes in all five languages.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1]).name))
