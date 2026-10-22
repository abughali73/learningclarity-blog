# Blog agent instructions

These are the instructions for the scheduled task that publishes a new post on blog.learningclarity.ai twice a day. The site is Jekyll on GitHub Pages: pushing to `main` publishes.

## Each run

1. **Pick the capability.** Read `_data/capabilities.yml`. Look at the `capability:` field of every file in `_posts/en/`. Choose the capability used least often; break ties by the one used longest ago, then by the order in the file. Never feature the same capability as the two most recent posts.
2. **Pick an angle.** Look at the titles of earlier posts on that capability and choose a different angle, for example: a how-to, a study scenario (exam week, a new job, a parent helping a child), a myth versus fact, or a "3 ways to" list. Write for individual learners, parents and teachers, and training teams in Europe and English-speaking markets.
3. **Write the English post** at `_posts/en/YYYY-MM-DD-<slug>.md`, using the current Cairo date. The slug is short, in English, lowercase and hyphenated, and not used by any earlier post. Set `date:` in the front matter to the current Cairo time minus 5 minutes, with Cairo's current UTC offset. Get both from `TZ=Africa/Cairo date -d '-5 min' '+%Y-%m-%d %H:%M:%S %z'`, because the offset changes with daylight saving. Jekyll skips future-dated posts, so the date must not be later than now.
   - 400 to 700 words, plain and friendly, short paragraphs, 2 to 4 `##` sections, and a short closing line. No title heading in the body; the layout shows the title.
   - Every product claim must come from that capability's `facts` (or another capability's facts). Never invent features, numbers, prices, testimonials, statistics or study results.
   - If the capability is `talk-to-this`, say that it is currently on the web app with mobile planned, and set `ad.footnote` to say the same.
4. **Write the Arabic post** at `_posts/ar/` with the same file name. Write it in natural Modern Standard Arabic; don't translate word for word. Keep the product name "LearningClarity" and the feature names in English the first time they appear, with an Arabic explanation (for example "وضع الشرح (Explain Mode)"). Use Western digits.
5. **Front matter.** Both files use the same `ref` (the slug) and `capability`. Use the `ad` block shape exactly as below. Write all text in that post's own language. Use exactly 4 `items`, each with 2 short `bullets` of under 60 characters. Choose `color` from blue, purple, pink or orange, and use a different one from the last post. Choose each `icon` from: upload, pencil, hierarchy, route, bulb, diagram, question, check, headphones, mic, people, bell, clipboard, chat, clock, award, globe, translate, swap, mail, user-plus, chart, gift, list, dollar, share, flame, star, device, layers, target.

```yaml
---
title: "Under 70 characters"
description: "One sentence, under 160 characters"
date: 2026-10-22 09:00:00 +0300   # from the command in step 3
lang: en            # ar for the Arabic file
ref: same-slug-in-both-files
capability: explain-mode
ad:
  color: purple
  eyebrow: "Explain Mode"
  headline: "An AI tutor that explains"
  highlight: "step by step"      # the gradient part, the end of the headline
  subtitle: "One short sentence."
  items:
    - icon: bulb
      title: "Simplify or go deeper"
      bullets: ["First bullet", "Second bullet"]
  footnote: ""                   # optional
---
```

6. **Check before publishing.** The YAML must parse (quote strings that contain a colon or a quote). Both files must exist with the same `ref`. The date must not be in the future. If a local Jekyll build is available, run `bundle exec jekyll build` or `jekyll build`; otherwise parse the front matter with Python's `yaml` module.
7. **Publish.** Commit both files to `main` with the message `post: <slug>`, then push. Never edit the layouts, CSS, `_config.yml`, `CNAME` or this file during a scheduled run.
8. **Report.** End with the post title and the live English and Arabic URLs: `https://blog.learningclarity.ai/en/YYYY/MM/<slug>/` and `/ar/YYYY/MM/<slug>/`. GitHub Pages takes about a minute to update.
