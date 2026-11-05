#!/usr/bin/env python3
"""Build the social-media drafts for one post and check them (AGENT.md step 9b).

Usage:
  python3 tools/make_social_drafts.py 2026-11-05-my-slug.md

From the English post it writes, in _social/<ref>/ (Jekyll ignores folders that start with "_",
so nothing here is published on the blog):
  linkedin-article.md  the LinkedIn article, structured exactly like the blog post: lead (description),
                       the same ## sections in the same order, every scene picture with its caption at the
                       same place, the FAQ, the hashtags and a link back to the original post
  README.md            the publishing checklist: title, cover picture, picture files, and the three posts

The agent writes these three files itself, in English, before running this script:
  linkedin-page.md      the post for the LearningClarity LinkedIn page
  linkedin-personal.md  the post for Maher's personal LinkedIn profile (first person)
  facebook.md           the post for the LearningClarity Facebook Page

The script then checks the three posts and exits with code 1 on any problem.
Picture copies sized for LinkedIn and Facebook are made by tools/generate_images.py in GitHub Actions.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://blog.learningclarity.ai"
POSTS = {
    "linkedin-page.md": ("LearningClarity LinkedIn page", 3000),
    "linkedin-personal.md": ("Maher's personal LinkedIn profile", 3000),
    "facebook.md": ("LearningClarity Facebook Page", 3000),
}


def load(path):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", path.read_text(encoding="utf-8").replace("\r\n", "\n"), re.S)
    return yaml.safe_load(m.group(1)), m.group(2)


def jpg(src, suffix=""):
    """The JPEG copy of a .webp picture (made by tools/generate_images.py), as an absolute URL."""
    return SITE + re.sub(r"\.webp$", f"{suffix}.jpg", src)


def table_to_list(lines):
    """LinkedIn articles have no tables: turn each row into one bullet, keeping every cell."""
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines]
    header, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
    out = []
    for r in body:
        parts = [f"{h}: {c}" for h, c in zip(header[1:], r[1:]) if c]
        out.append(f"- **{r[0]}**: " + "; ".join(parts) + ".")
    return out


def article(fm, body, url):
    scenes = fm.get("scenes") or []
    out, table = [f"*{fm['description']}*", ""], []

    def flush():
        if table:
            out.extend(table_to_list(table))
            table.clear()

    for line in body.strip("\n").split("\n"):
        if line.lstrip().startswith("|"):
            table.append(line)
            continue
        flush()
        m = re.fullmatch(r"\s*\{% include scene\.html n=(\d+) %\}\s*", line)
        if m:
            s = scenes[int(m.group(1)) - 1]
            out += [f"![{s['alt']}]({jpg(s['src'])})", f"*{s['caption']}*"]
            continue
        if re.search(r"\{%|<iframe|<figure", line):
            continue  # Liquid tags and embeds do not exist on LinkedIn
        out.append(re.sub(r"\]\((/[^)]*)\)", lambda m: f"]({SITE}{m.group(1)})", line))
    flush()
    if fm.get("faq"):
        out += ["", "## Frequently asked questions", ""]
        for f in fm["faq"]:
            out += [f"**{f['q']}**", "", f["a"], ""]
    out += ["", " ".join("#" + t for t in fm.get("tags") or []), "",
            f"*Originally published on the [LearningClarity blog]({url}).*"]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"


def readme(fm, url, folder):
    hero = fm["hero_image"]["src"]
    lines = [
        f"# Social drafts: {fm['title']}", "",
        f"Blog post: {url}", "",
        "## 1. LinkedIn article (LearningClarity page and personal profile)", "",
        "LinkedIn does not allow articles to be published automatically, so publish it by hand: "
        "Write article (from the page's admin view for the LearningClarity page, or from your profile), then:", "",
        f"1. **Cover picture** (1920 x 1080, 16:9 JPEG, as LinkedIn recommends): [{Path(jpg(hero, '-linkedin')).name}]({jpg(hero, '-linkedin')})",
        f"2. **Title**: {fm['title']}",
        "3. **Body**: open [linkedin-article.md](linkedin-article.md), copy the rendered text and paste it under the title. "
        "Where a picture appears, upload the JPEG listed below at that place and paste its caption.",
        "4. Publish once on the LearningClarity page and once on your profile (or publish on one and share it from the other).", "",
        "Pictures, in order:", "",
    ]
    for i, s in enumerate(fm.get("scenes") or [], 1):
        lines.append(f"- Scene {i}: [{Path(jpg(s['src'])).name}]({jpg(s['src'])}): *{s['caption']}*")
    lines += ["", "## 2. Posts", "",
              f"Feed picture for all three posts (1200 x 627, 1.91:1 JPEG): [{Path(jpg(hero, '-feed')).name}]({jpg(hero, '-feed')})", ""]
    for name, (where, _) in POSTS.items():
        lines += [f"### {where}", "", (folder / name).read_text(encoding="utf-8").strip(), ""]
    lines += ["Pictures appear a few minutes after the image workflow has run.", ""]
    return "\n".join(lines)


def check_posts(folder, url):
    problems = []
    for name, (where, limit) in POSTS.items():
        path = folder / name
        if not path.exists():
            problems.append(f"{name} is missing (the post for the {where})")
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not 300 <= len(text) <= limit:
            problems.append(f"{name}: {len(text)} characters (300 to {limit})")
        if url not in text:
            problems.append(f"{name}: add the link to the blog post ({url})")
        if not 3 <= len(re.findall(r"(?<!\w)#\w", text)) <= 6:
            problems.append(f"{name}: use 3 to 6 hashtags")
        if re.search(r"(?i)\bAI study app\b", text):
            problems.append(f'{name}: say "study platform", not "AI study app"')
        if "fictional" not in text.lower():
            problems.append(f"{name}: say that the people in the story are fictional")
    return problems


def main(name):
    path = ROOT / "_posts" / "en" / name
    if not path.exists():
        sys.exit(f"{path.relative_to(ROOT)} not found")
    fm, body = load(path)
    m = re.match(r"(\d{4})-(\d{2})-\d{2}-(.+)\.md$", name)
    url = f"{SITE}/en/{m.group(1)}/{m.group(2)}/{m.group(3)}/"
    folder = ROOT / "_social" / fm["ref"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "linkedin-article.md").write_text(article(fm, body, url), encoding="utf-8")
    problems = check_posts(folder, url)
    if problems:
        print("Problems:\n- " + "\n- ".join(problems))
        return 1
    (folder / "README.md").write_text(readme(fm, url, folder), encoding="utf-8")
    print(f"OK: social drafts for {name} are in _social/{fm['ref']}/")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1]).name))
