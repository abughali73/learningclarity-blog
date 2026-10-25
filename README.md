# LearningClarity blog

Source for https://blog.learningclarity.ai, a Jekyll site published with GitHub Pages from the `main` branch.

- Languages: English, Arabic, Spanish, French and German, listed under `languages:` in `_config.yml`. Posts live in `_posts/<code>/` (en, ar, es, fr, de); the five files of a post share a file name and a `ref`, which the layouts use for the language menu, the "Also available in" links, `hreflang` and schema translations (`_includes/lang-links.html`, `_includes/lang-switcher.html`).
- Language home pages: `/`, `/ar/`, `/es/`, `/fr/`, `/de/`. Interface text: `_data/i18n.yml`. Author texts per language: `_data/authors.yml` (`_ar`, `_es`, `_fr`, `_de` keys).
- To add a language: add it to `languages:` and `defaults:` in `_config.yml` and to `feed.categories`, add its strings to `_data/i18n.yml` and author keys to `_data/authors.yml`, and create `<code>/index.html` and `<code>/author/maher-abu-ghali.html`.
- The ad infographic on each post comes from the post's `ad:` front matter (`_includes/ad.html`).
- `_data/capabilities.yml` holds the product facts that posts may use.
- `AGENT.md` holds the instructions for the scheduled task that publishes one post every two days.
- Author: `_data/authors.yml` (default author for every post). Social links: `_data/social.yml`.
- SEO tags and schema: `_includes/seo.html` (BlogPosting, Person, Organization, FAQPage, VideoObject). `llms.txt` lists every post for AI search tools.
- Preview images: `python3 tools/render_previews.py` renders each post's infographic to `assets/img/posts/`.
- AI illustrations: posts with a `hero_image.prompt` get an image from `.github/workflows/generate-images.yml` (needs the Gemini API key in the `OPENAI_API_KEY` secret; the model comes from the `OPENAI_MODEL` variable, default `gemini-flash-latest`).
- Search engine verification codes go in `_config.yml` under `verification:`.
