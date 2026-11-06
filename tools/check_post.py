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
        if not 50 <= len(fm.get("title", "")) <= 70:
            p(f"title is {len(fm.get('title', ''))} characters (50 to 70)")
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
        if not ad.get("eyebrow") or len(ad.get("eyebrow", "")) > 36:
            p("ad.eyebrow is needed and must be 36 characters or fewer (it is the card label on the home and search pages)")
        if re.search(r"(?i)\bAI study app\b", (fm.get("title", "") + " " + fm.get("description", "") + " " + body)):
            p('say "study platform", not "AI study app"')
        if re.search(r"adsbygoogle|googlesyndication", body):
            p("remove the ad code from the body; the layouts place ads")
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
            if src and not src.endswith(".webp"):
                p(f"{src} must end in .webp")
    # story library: the idea must exist, be writable, and not be used by another post
    lib_path = ROOT / "_data" / "story_library.yml"
    en = posts.get("en", ({}, ""))[0]
    story = en.get("story")
    if story and lib_path.exists():
        lib = yaml.safe_load(lib_path.read_text(encoding="utf-8")) or {}
        ideas = {i.get("id"): i for i in lib.get("ideas") or []}
        if story not in ideas:
            problems.append(f"story {story!r} is not an idea in _data/story_library.yml")
        elif ideas[story].get("status") != "idea":
            problems.append(f"story {story!r} has status {ideas[story].get('status')!r}; only 'idea' entries may be written")
        for other in (ROOT / "_posts" / "en").glob("*.md"):
            if other.name != name:
                try:
                    if load(other)[0].get("story") == story:
                        problems.append(f"story {story!r} is already used by {other.name}")
                except Exception:
                    pass
        for lang, (fm, _) in posts.items():
            if fm.get("story") != story:
                problems.append(f"{lang}: story must be {story!r} in all five files")
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
    # feature-update posts (layout: feature-update): the features block, its clips and the section anchors
    if posts.get("en") and posts["en"][0].get("layout") == "feature-update":
        problems += check_feature_update(posts)
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


def check_feature_update(posts):
    """Rules for the weekly feature-update announcement (skill lc-features-update)."""
    out = []
    en = posts["en"][0]
    ref = en.get("ref")
    feats_en = en.get("features") or []
    if not 3 <= len(feats_en) <= 7:
        out.append(f"en: {len(feats_en)} features (need 3 to 7)")
    ids = [f.get("id") for f in feats_en]
    if len(set(ids)) != len(ids):
        out.append("en: feature ids must be unique")
    total = 0
    for lang, (fm, body) in posts.items():
        p = lambda msg: out.append(f"{lang}: {msg}")
        if fm.get("layout") != "feature-update":
            p("layout must be feature-update in all five files")
        if fm.get("feature_update") is not True:
            p("feature_update: true is missing")
        if not isinstance(fm.get("issue"), int) or fm.get("issue") != en.get("issue"):
            p("issue must be the same whole number in all five files")
        feats = fm.get("features") or []
        if [(f.get("id"), f.get("icon"), bool(f.get("clip")), bool(f.get("web_only"))) for f in feats] != \
                [(f.get("id"), f.get("icon"), bool(f.get("clip")), bool(f.get("web_only"))) for f in feats_en]:
            p("features differ from en (ids, order, icons, clip or web_only)")
        for f in feats:
            fid = f.get("id") or "?"
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(fid)):
                p(f"feature id {fid!r} must be lowercase words joined by hyphens")
            if f.get("icon") not in ICONS:
                p(f"feature {fid}: icon {f.get('icon')!r} is not a known icon")
            for key in ("title", "summary"):
                if not f.get(key):
                    p(f"feature {fid}: {key} is missing")
            if len(f.get("summary", "")) > 110:
                p(f"feature {fid}: summary is {len(f.get('summary', ''))} characters (110 max)")
            if not re.search(r"^## .*\{#f-" + re.escape(str(fid)) + r"\}\s*$", body, re.M):
                p(f"feature {fid}: no section heading ending in {{#f-{fid}}}")
            n = len(re.findall(r'\{% include feature-clip\.html id="' + re.escape(str(fid)) + r'" %\}', body))
            if f.get("clip"):
                if n != 1:
                    p(f"feature {fid}: feature-clip is included {n} times (need exactly 1)")
                if not f.get("alt") or not f.get("caption"):
                    p(f"feature {fid}: a clip needs alt and caption")
            elif n:
                p(f"feature {fid}: clip is not true but the body includes its clip")
        for m in re.findall(r'\{% include feature-clip\.html id="([^"]+)" %\}', body):
            if m not in ids:
                p(f"the body includes a clip for unknown feature {m!r}")
        if "<video" in body:
            p("use {% include feature-clip.html %} instead of a <video> tag")
    for f in feats_en:
        if not f.get("clip"):
            continue
        base = ROOT / "assets" / "video" / "features" / str(ref) / str(f.get("id"))
        for suffix in (".mp4", "-poster.jpg"):
            path = Path(str(base) + suffix)
            if not path.exists():
                out.append(f"feature {f.get('id')}: {path.relative_to(ROOT)} is missing")
        for path in base.parent.glob(f"{f.get('id')}*"):
            size = path.stat().st_size
            total += size
            if path.suffix in (".mp4", ".webm") and size > 4 * 1024 * 1024:
                out.append(f"{path.relative_to(ROOT)} is {size / 1048576:.1f} MB (4 MB max per clip)")
    if total > 20 * 1024 * 1024:
        out.append(f"the clips and narration of this post total {total / 1048576:.1f} MB (20 MB max)")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1]).name))
