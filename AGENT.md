# Blog agent instructions

These are the instructions for the scheduled task that publishes a new post on blog.learningclarity.ai every two days. The site is Jekyll on GitHub Pages: pushing to `main` publishes.

Every post is published in **five languages**: English (`en`), Arabic (`ar`), Spanish (`es`), French (`fr`) and German (`de`). The languages are listed under `languages:` in `_config.yml`. Each language has its own folder (`_posts/<code>/`), home page (`/`, `/ar/`, `/es/`, `/fr/`, `/de/`), author page and feed (`/feed/<code>.xml`). All five files of a post share the same file name and the same `ref`; the layouts use the `ref` to cross-reference the languages automatically (the header language menu, the "Also available in" links under the title, `hreflang` tags, and `workTranslation`/`translationOfWork` in the schema). Never publish a post in fewer than five languages.

## Each run

1. **Pick the capability.** Read `_data/capabilities.yml`. Look at the `capability:` field of every file in `_posts/en/`. Skip capabilities marked `hold: true`, and ignore posts whose `capability:` is not in the file (such as `faq`). Choose the capability used least often; break ties by the one used longest ago, then by the order in the file. Never feature the same capability as the two most recent posts.
2. **Pick an angle.** Look at the titles of earlier posts on that capability and choose a different angle, for example: a how-to, a study scenario (exam week, a new job, a parent helping a child), a myth versus fact, or a "3 ways to" list. Write for individual learners, parents and teachers, and training teams in Europe and English-speaking markets.
3. **Write the English post** at `_posts/en/YYYY-MM-DD-<slug>.md`, using the current Cairo date. The slug is short, in English, lowercase and hyphenated, and not used by any earlier post. Set `date:` in the front matter to the current Cairo time minus 5 minutes, with Cairo's current UTC offset. Get both from `TZ=Africa/Cairo date -d '-5 min' '+%Y-%m-%d %H:%M:%S %z'`, because the offset changes with daylight saving. Jekyll skips future-dated posts, so the date must not be later than now.
   - 400 to 700 words, plain and friendly, short paragraphs, 2 to 4 `##` sections, and a short closing line. No title heading in the body; the layout shows the title.
   - Every product claim must come from that capability's `facts` (or another capability's facts). Never invent features, numbers, prices, testimonials, statistics or study results.
   - If the capability is `talk-to-this`, say that it is currently on the web app with mobile planned, and set `ad.footnote` to say the same.
4. **Write the Arabic post** at `_posts/ar/` with the same file name. Write it in natural Modern Standard Arabic; don't translate word for word. Keep the product name "LearningClarity" and the feature names in English the first time they appear, with an Arabic explanation (for example "وضع الشرح (Explain Mode)"). Use the same Arabic feature names as earlier Arabic posts (for example وضع الاختبار القصير (Quiz Mode), وضع الامتحان (Exam Mode)). Use Western digits.
4b. **Write the Spanish, French and German posts** at `_posts/es/`, `_posts/fr/` and `_posts/de/`, again with the same file name. Write each one natively for readers in Spain and Latin America, France, Belgium and Switzerland, and Germany, Austria and Switzerland; don't translate word for word. Keep "LearningClarity" and the feature names in English the first time they appear, followed by a short explanation in brackets (for example "Explain Mode (modo explicación)", "Explain Mode (mode explication)", "Explain Mode (Erklärmodus)"). Use the polite form in German (Sie) and French (vous), and "tú" in Spanish. Use correct typography: French puts a space before `:`, `?` and `!` and uses « guillemets »; German uses „Anführungszeichen“. Every claim must still come from `_data/capabilities.yml`.
5. **Front matter.** All five files use the same `ref` (the slug), `capability`, `ad.color`, `ad.items[].icon` and `hero_image` `src` and `prompt`. Use the `ad` block shape exactly as below. Write all text in that post's own language. Use exactly 4 `items`, each with 2 short `bullets` of under 60 characters. Choose `color` from blue, purple, pink or orange, and use a different one from the last post. Choose each `icon` from: upload, pencil, hierarchy, route, bulb, diagram, question, check, headphones, mic, people, bell, clipboard, chat, clock, award, globe, translate, swap, mail, user-plus, chart, gift, list, dollar, share, flame, star, device, layers, target.

```yaml
---
title: "Under 70 characters"
description: "One sentence, under 160 characters"
date: 2026-10-22 09:00:00 +0300   # from the command in step 3
lang: en            # ar for the Arabic file
ref: same-slug-in-both-files
capability: explain-mode
keywords: ["AI study tutor", "step-by-step explanations", "learn at your own pace"]
tags: [LearningClarity, LearningClarityAI, ExplainMode, AITutor, StudyTips, OnlineLearning, EdTech, AIinEducation, Students, LifelongLearning]
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
hero_image:                      # optional AI illustration, generated after you push (see step 5b)
  src: /assets/img/posts/<slug>-hero.png    # same src in both language files
  alt: "Describe the picture in this post's language"
  prompt: "In English: what to draw. A scene, not a diagram. No text, logos or real people."
faq:                             # 2 or 3 short questions a reader would search for
  - q: "A question in this post's language?"
    a: "A 1 to 3 sentence answer that uses only facts from capabilities.yml."
---
```

   The author (Dr. Maher Abu Ghali) is set automatically for every post; do not add an `author:` field. Do not add an `image:` field by hand; step 7 sets it.

5b. **AI illustration (optional, recommended).** Add the `hero_image` block above. Use the same `src` and `prompt` in all five language files, so one image serves every language. Write `alt` in each post's own language. You cannot call the image API from your sandbox. After you push, a GitHub Actions workflow (`.github/workflows/generate-images.yml`) generates the picture with Google Gemini and commits it. The post shows the picture once the file exists. Keep prompts generic and safe: no text in the image, no logos, no real or recognisable people, nothing that looks like a screenshot of the product.

6. **SEO and hashtags.** Apply these to all five languages. Research the primary phrase separately for each language (what a Spanish, French or German learner would actually type), rather than translating the English one.
   - **Keyword:** pick one primary search phrase a learner would type, such as "AI study tutor", "how to revise for exams", or "تطبيق تعليمي بالذكاء الاصطناعي" for Arabic. Add 3 to 5 related phrases. Put them in `keywords:`, primary first, written in that post's language.
   - **Title:** 50 to 65 characters, with the primary phrase near the start.
   - **Description:** 140 to 160 characters, with the primary phrase, written as a reason to click.
   - **Slug:** 3 to 6 English words that include the primary phrase.
   - **Body:**
     - Use the primary phrase in the first 2 sentences and in at least one `##` heading.
     - Use the related phrases naturally, never stuffed.
     - Add one internal link to an earlier post in the same language (relative URL, descriptive anchor text, for example `/es/2026/10/<slug>/`) when one exists. Never link from one language to a post in another language in the body; the layout adds the cross-language links.
     - Add one link to https://www.learningclarity.ai with descriptive anchor text, not "click here".
   - **Hashtags:** add `tags:` with 10 to 15 hashtags, written without the `#` (the layout adds it), in CamelCase with no spaces. Mix these kinds:
     - brand: LearningClarity, LearningClarityAI;
     - feature: for example ExplainMode, AIPodcast;
     - topic: for example StudyTips, ExamPrep, OnlineLearning, EdTech, AIinEducation;
     - audience: for example Students, Teachers, Parents, LifelongLearning, CorporateTraining.

     Spanish, French and German posts mix hashtags in that language (written without accents where that is the common usage, for example AprendizajeOnline, ApprentissageEnLigne; German keeps umlauts, for example KünstlicheIntelligenz) with the 2 brand hashtags and 2 or 3 English ones (EdTech, AIinEducation, LifelongLearning).

     Arabic posts mix Arabic hashtags (use `_` between words, for example تعلم_ذاتي, الذكاء_الاصطناعي, نصائح_دراسية, التعليم_الإلكتروني) with the 2 brand hashtags and 2 or 3 English ones. Use only real, commonly used hashtags. Never repeat a hashtag within one post.
7. **Preview images.** Run `python3 tools/render_previews.py _posts/en/<file> _posts/ar/<file> _posts/es/<file> _posts/fr/<file> _posts/de/<file>`. It renders each post's infographic to `assets/img/posts/<lang>-<slug>.png` (the preview image for search results and social shares) and sets `image:` in the front matter. Open the Arabic PNG and one of the others to check they rendered correctly.
8. **Check before publishing.** The YAML must parse (quote strings that contain a colon or a quote). All five files must exist with the same `ref`. Each must have `keywords` and 10 to 15 `tags` with no `#` and no spaces, and each `faq` item must have `q` and `a`. The date must not be in the future. If a local Jekyll build is available, run `bundle exec jekyll build` or `jekyll build`; otherwise parse the front matter with Python's `yaml` module.
9. **Publish.** Commit the five post files and their five preview PNGs to `main` with the message `post: <slug>`, then push. Never edit the layouts, includes, CSS, `_config.yml`, `_data/`, `CNAME`, `tools/`, `.github/` or this file during a scheduled run.
10. **Report.** End with the post title and the five live URLs: `https://blog.learningclarity.ai/<code>/YYYY/MM/<slug>/` for `en`, `ar`, `es`, `fr` and `de`. GitHub Pages takes about a minute to update.
