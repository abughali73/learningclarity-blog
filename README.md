# LearningClarity blog

Source for https://blog.learningclarity.ai, a Jekyll site published with GitHub Pages from the `main` branch.

- English posts: `_posts/en/`. Arabic posts: `_posts/ar/` (the two files of a pair share a `ref`).
- The ad infographic on each post comes from the post's `ad:` front matter (`_includes/ad.html`).
- `_data/capabilities.yml` holds the product facts that posts may use.
- `AGENT.md` holds the instructions for the scheduled task that publishes one post every two days.
- Author: `_data/authors.yml` (default author for every post). Social links: `_data/social.yml`.
- SEO tags and schema: `_includes/seo.html` (BlogPosting, Person, Organization, FAQPage, VideoObject). `llms.txt` lists every post for AI search tools.
- Preview images: `python3 tools/render_previews.py` renders each post's infographic to `assets/img/posts/`.
- AI illustrations: posts with a `hero_image.prompt` get an image from `.github/workflows/generate-images.yml` (needs the `OPENAI_API_KEY` secret and the `OPENAI_IMAGE_MODEL` variable).
- Search engine verification codes go in `_config.yml` under `verification:`.
