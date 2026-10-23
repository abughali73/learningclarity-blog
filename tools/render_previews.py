#!/usr/bin/env python3
"""Render each post's infographic (the `ad:` block) to a PNG and use it as the post's preview image.

Usage:
  python3 tools/render_previews.py              # posts that have no image yet
  python3 tools/render_previews.py --all        # re-render every post with an ad block
  python3 tools/render_previews.py _posts/en/2026-10-23-my-post.md _posts/ar/2026-10-23-my-post.md

For each post it writes assets/img/posts/<lang>-<slug>.png (the same figure readers see in the
post) and sets `image:` in the front matter. Posts whose `image:` points elsewhere (for example a
video poster) are left alone unless they are named on the command line.

Needs: python3, PyYAML, playwright (Chromium) and npm (to fetch the web fonts once).
"""
import base64
import html
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "img" / "posts"
FONT_CACHE = Path(os.environ.get("LC_FONT_CACHE", Path(tempfile.gettempdir()) / "lc-fonts"))
FONT_PACKAGES = {
    "poppins": ("@fontsource/poppins@5.3.0", "Poppins", ["latin-600", "latin-700", "latin-800"]),
    "inter": ("@fontsource/inter@5.3.0", "Inter", ["latin-400", "latin-500", "latin-600"]),
    "ibm-plex-sans-arabic": ("@fontsource/ibm-plex-sans-arabic@5.3.0", "IBM Plex Sans Arabic",
                             ["arabic-400", "arabic-500", "arabic-600", "arabic-700",
                              "latin-400", "latin-500", "latin-600", "latin-700"]),
}
COLORS = ["blue", "purple", "pink", "orange"]


def font_faces():
    FONT_CACHE.mkdir(parents=True, exist_ok=True)
    css = []
    for key, (pkg, family, variants) in FONT_PACKAGES.items():
        files = FONT_CACHE / key / "package" / "files"
        if not files.exists():
            dest = FONT_CACHE / key
            dest.mkdir(parents=True, exist_ok=True)
            out = subprocess.run(["npm", "pack", pkg, "--silent"], cwd=dest, check=True,
                                 capture_output=True, text=True).stdout.strip().splitlines()[-1]
            with tarfile.open(dest / out) as tar:
                tar.extractall(dest, filter="data") if hasattr(tarfile, "data_filter") else tar.extractall(dest)
        for v in variants:
            subset, weight = v.rsplit("-", 1)
            f = files / f"{key}-{subset}-{weight}-normal.woff2"
            if f.exists():
                css.append(f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:normal;"
                           f"src:url(data:font/woff2;base64,{base64.b64encode(f.read_bytes()).decode()}) format('woff2');}}")
    return "\n".join(css)


def icon_svgs():
    src = (ROOT / "_includes" / "icon.html").read_text()
    icons = {}
    for m in re.finditer(r"\{%-?\s*when\s+'([\w-]+)'\s*-?%\}(.*?)(?=\{%-?\s*(?:when|endcase))", src, re.S):
        icons[m.group(1)] = m.group(2).strip()
    return icons


def split_post(path):
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError(f"{path}: no front matter")
    return text, m.group(1), yaml.safe_load(m.group(1))


def ad_html(ad, lang, i18n, icons):
    t = i18n[lang]
    e = html.escape
    steps = []
    for i, item in enumerate(ad["items"][:4]):
        c = COLORS[i]
        svg = (f'<svg class="icon" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
               f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
               f'{icons.get(item["icon"], "")}</svg>')
        bullets = "".join(f"<li>{e(b)}</li>" for b in item["bullets"][:2])
        steps.append(f'<li class="ad-step ad-{c}"><span class="ad-icon">{svg}</span>'
                     f'<span class="ad-link" aria-hidden="true"></span><div class="ad-card">'
                     f'<span class="ad-num">{i + 1}</span><div><div class="ad-title">{e(item["title"])}</div>'
                     f'<ul class="ad-bullets">{bullets}</ul></div></div></li>')
    def img(name):
        data = base64.b64encode((ROOT / "assets" / "img" / name).read_bytes()).decode()
        return f"data:image/png;base64,{data}"
    stores = f"""<div class="stores">
  <a class="store"><img src="{img("qr-ios.png")}" alt="" width="96" height="96"><span><small>{e(t['ios_small'])}</small><strong>{e(t['ios_big'])}</strong><small>{e(t['ios_note'])}</small></span></a>
  <a class="store"><img src="{img("qr-android.png")}" alt="" width="96" height="96"><span><small>{e(t['android_small'])}</small><strong>{e(t['android_big'])}</strong><small>{e(t['android_note'])}</small></span></a>
  <a class="store"><img src="{img("qr-web.png")}" alt="" width="96" height="96"><span><small>{e(t['web_small'])}</small><strong class="web">{e(t['web_big'])}</strong><small>{e(t['web_note'])}</small></span></a>
</div>"""
    foot = f'<figcaption class="ad-footnote">{e(ad["footnote"])}</figcaption>' if ad.get("footnote") else ""
    return f"""<figure class="ad" dir="{'rtl' if lang == 'ar' else 'ltr'}">
  <div class="ad-brand"><img src="{img("lc-icon.png")}" alt="" width="56" height="56"><div>
    <div class="ad-wordmark">Learning <span class="grad">Clarity</span></div>
    <div class="ad-tagline">Clarity in Learning. Success in Every Step.</div></div></div>
  <div class="ad-hero"><span class="ad-eyebrow ad-eyebrow-{e(ad.get('color', 'blue'))}">{e(ad['eyebrow'])}</span>
    <div class="ad-headline">{e(ad['headline'])} <span class="grad">{e(ad['highlight'])}</span></div>
    <p class="ad-sub">{e(ad['subtitle'])}</p></div>
  <ol class="ad-steps">{''.join(steps)}</ol>
  {stores}{foot}
</figure>"""


def set_image(path, text, fm_text, rel):
    if re.search(r"^image:.*$", fm_text, re.M):
        new_fm = re.sub(r"^image:.*$", f"image: {rel}", fm_text, count=1, flags=re.M)
    else:
        new_fm = re.sub(r"^(capability:.*)$", rf"\1\nimage: {rel}", fm_text, count=1, flags=re.M)
        if new_fm == fm_text:
            new_fm = fm_text + f"\nimage: {rel}"
    path.write_text(text.replace(fm_text, new_fm, 1))


def main(argv):
    from playwright.sync_api import sync_playwright

    render_all = "--all" in argv
    named = [ROOT / a if not os.path.isabs(a) else Path(a) for a in argv if not a.startswith("--")]
    posts = named or sorted((ROOT / "_posts").glob("*/*.md"))
    i18n = yaml.safe_load((ROOT / "_data" / "i18n.yml").read_text())
    icons = icon_svgs()
    css = (ROOT / "assets" / "css" / "style.css").read_text()
    faces = font_faces()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done = []
    with sync_playwright() as p:
        exe = "/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").exists() else None
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=2)
        for path in posts:
            text, fm_text, fm = split_post(path)
            ad = fm.get("ad")
            if not ad:
                continue
            lang = fm.get("lang") or path.parent.name
            slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)
            rel = f"/assets/img/posts/{lang}-{slug}.png"
            current = fm.get("image")
            if current and current != rel and path not in named:
                continue  # custom image such as a video poster
            if current == rel and not render_all and path not in named and (ROOT / rel.lstrip("/")).exists():
                continue
            doc = f"""<!doctype html><html lang="{lang}" dir="{'rtl' if lang == 'ar' else 'ltr'}"><head><meta charset="utf-8">
<style>{faces}\n{css}\nbody{{background:#fff;margin:0;padding:0}} .post .ad, .ad{{margin:0}}</style></head>
<body class="lang-{lang}"><main class="wrap" style="max-width:1080px;padding:0"><article class="post">{ad_html(ad, lang, i18n, icons)}</article></main></body></html>"""
            page.set_content(doc, wait_until="load")
            page.evaluate("document.fonts.ready")
            out = ROOT / rel.lstrip("/")
            page.locator("figure.ad").screenshot(path=str(out), animations="disabled")
            set_image(path, text, fm_text, rel)
            done.append(f"{path.relative_to(ROOT)} -> {rel}")
        browser.close()
    print("\n".join(done) if done else "nothing to render")


if __name__ == "__main__":
    main(sys.argv[1:])
