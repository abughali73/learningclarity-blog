# Blog agent instructions

These are the instructions for the scheduled task that publishes a new post on blog.learningclarity.ai every two days. The site is Jekyll on GitHub Pages: pushing to `main` publishes.

Every post is published in **five languages**: English (`en`), Arabic (`ar`), Spanish (`es`), French (`fr`) and German (`de`). The languages are listed under `languages:` in `_config.yml`. Each language has its own folder (`_posts/<code>/`), home page (`/`, `/ar/`, `/es/`, `/fr/`, `/de/`), author page and feed (`/feed/<code>.xml`). All five files of a post share the same file name and the same `ref`; the layouts use the `ref` to cross-reference the languages automatically (the header language menu, the "Also available in" links under the title, `hreflang` tags, and `workTranslation`/`translationOfWork` in the schema). Never publish a post in fewer than five languages.

## Each run

1. **Pick the capability.** Read `_data/capabilities.yml`. Look at the `capability:` field of every file in `_posts/en/`. Skip capabilities marked `hold: true`, and ignore posts whose `capability:` is not in the file (such as `faq`). Choose the capability used least often; break ties by the one used longest ago, then by the order in the file. Never feature the same capability as the two most recent posts.
2. **Pick an angle, and tell it as a story.** Look at the titles of earlier posts on that capability and choose a different angle. By default, write the post as a short story about one fictional learner (a student before an exam, a parent helping a child, a teacher, a professional starting a new job, a team lead training staff): a real situation with something at stake, a few moments over days or a week, a setback, and an ending where the learning pays off. Weave the product into the story as things the character does (for example tapping Simplify when a term is confusing, or turning a subtopic into a podcast for the train), not as a feature list; show the featured capability in depth and 2 to 4 related capabilities along the way. Write for individual learners, parents and teachers, and training teams in Europe and English-speaking markets.
   - **Character.** Give the character a first name not used in any earlier post: check the names in earlier posts and in their `scenes` prompts (`grep -ohE "[A-Z][a-z]+, a (fictional|[0-9])" -r _posts/en | sort -u` lists most of them; also read the recent posts). Vary age, background and situation from the last few posts. Say once in the body that the person is fictional, and set `ad.footnote` to say so too.
3. **Write the English post** at `_posts/en/YYYY-MM-DD-<slug>.md`, using the current Cairo date. The slug is short, in English, lowercase and hyphenated, and not used by any earlier post. Set `date:` in the front matter to the current Cairo time minus 5 minutes, with Cairo's current UTC offset. Get both from `TZ=Africa/Cairo date -d '-5 min' '+%Y-%m-%d %H:%M:%S %z'`, because the offset changes with daylight saving. Jekyll skips future-dated posts, so the date must not be later than now.
   - 550 to 800 words, plain and friendly, short paragraphs, 3 to 6 `##` sections (for a story, one per moment, for example "Sunday: ..."), and a short closing line that invites the reader to start. No title heading in the body; the layout shows the title. Don't add app-store links or QR codes; the layout shows them at the end of every page.
   - **Name and wording.** Call the product "LearningClarity" and describe it as an AI-powered study platform (for example "the LearningClarity study platform"), never as an "AI study app". In other languages use the same idea: منصة Learning Clarity للدراسة, plataforma de estudio, plateforme d'étude, Lernplattform.
   - Every product claim must come from that capability's `facts` (or another capability's facts). Never invent features, numbers, prices, testimonials, statistics or study results.
4. **Write the Arabic post** at `_posts/ar/` with the same file name. Write it in natural Modern Standard Arabic; don't translate word for word. Keep the product name "LearningClarity" and the feature names in English the first time they appear, with an Arabic explanation (for example "وضع الشرح (Explain Mode)"). Use the same Arabic feature names as earlier Arabic posts (for example وضع الاختبار القصير (Quiz Mode), وضع الامتحان (Exam Mode)). Use Western digits.
4b. **Write the Spanish, French and German posts** at `_posts/es/`, `_posts/fr/` and `_posts/de/`, again with the same file name. Write each one natively for readers in Spain and Latin America, France, Belgium and Switzerland, and Germany, Austria and Switzerland; don't translate word for word. Keep "LearningClarity" and the feature names in English the first time they appear, followed by a short explanation in brackets (for example "Explain Mode (modo explicación)", "Explain Mode (mode explication)", "Explain Mode (Erklärmodus)"). Use the polite form in German (Sie) and French (vous), and "tú" in Spanish. Use correct typography: French puts a space before `:`, `?` and `!` and uses « guillemets »; German uses „Anführungszeichen“. Every claim must still come from `_data/capabilities.yml`.
5. **Front matter.** All five files use the same `ref` (the slug), `capability`, `ad.color`, `ad.items[].icon`, `hero_image` `src` and `prompt`, and `scenes` `src` and `prompt`. Use the `ad` block shape exactly as below. Write all text in that post's own language. Use exactly 4 `items`, each with 2 short `bullets` of under 60 characters. Choose `color` from blue, purple, pink or orange, and use a different one from the last post. Choose each `icon` from: upload, pencil, hierarchy, route, bulb, diagram, question, check, headphones, mic, people, bell, clipboard, chat, clock, award, globe, translate, swap, mail, user-plus, chart, gift, list, dollar, share, flame, star, device, layers, target.

```yaml
---
title: "Under 70 characters"
description: "One sentence, under 160 characters"
date: 2026-10-22 09:00:00 +0300   # from the command in step 3
lang: en            # ar for the Arabic file
ref: same-slug-in-both-files
capability: explain-mode
image: /assets/img/posts/<slug>-cinematic.webp   # always the hero_image src (step 7)
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
  footnote: "Lena is a fictional learner."   # name the fictional character; add any required note
hero_image:                      # required AI illustration, generated after you push (see step 5b)
  src: /assets/img/posts/<slug>-cinematic.webp    # same src in all five language files
  alt: "Describe the picture in this post's language"
  prompt: "In English: what to draw. A scene, not a diagram. No text, logos or real people."
scenes:                          # required: 4 to 7 in-post scene images, generated after you push (see step 5b)
  - src: /assets/img/posts/<slug>-scene-1.webp  # same src and prompt in all five language files
    alt: "Describe the picture in this post's language"
    caption: "A short caption in this post's language"
    prompt: "In English: one story moment, staged like a film shot. No text, logos or real people."
faq:                             # 2 or 3 short questions a reader would search for
  - q: "A question in this post's language?"
    a: "A 1 to 3 sentence answer that uses only facts from capabilities.yml."
---
```

   The author (Dr. Maher Abu Ghali) is set automatically for every post; do not add an `author:` field. Set the `image:` field as described in step 7. Look at `_posts/en/2026-10-27-online-learning-certificate-journey.md` for a complete example of a story post with its hero image and scenes.

5a. **How the post is listed.** The home pages and the search pages (`/search/`, `/ar/search/` and so on) list every post as a card: the hero picture on the left, then `ad.eyebrow` as a small coloured label, the `title`, the `description` and the date. So keep `ad.eyebrow` short (36 characters or fewer, a feature or theme name such as "Exam Mode" or "From sign-up to certificate"), and write the `description` as a one-sentence reason to read that makes sense on its own. The search box searches the title, description, keywords, hashtags, FAQ and full text, so use the words a reader would actually type.

5b. **Images (required): cinematic, and plenty of them.** Every post is visual. It has one `hero_image` (shown at the top, and used as the preview image) and 4 to 7 `scenes` (shown inside the post). All of them are generated with OpenAI's image model (the model behind ChatGPT image generation) in a cinematic film-still style. You cannot call the image API from your sandbox, and you must never draw, render or commit images yourself. After you push, a GitHub Actions workflow (`.github/workflows/generate-images.yml`) generates every missing picture and commits it; each picture appears once its file exists.
   - Every image `src` ends in `.webp`. The workflow saves each picture as a compressed WebP in two sizes (1280 and 640 pixels wide, so pages load fast) and the hero also as a JPEG for social-media previews; the layouts pick the right file automatically.
   - Use the same `src` and `prompt` for each image in all five language files, so one image serves every language. Write `alt` and `caption` in each post's own language. Name scene files `<slug>-scene-1.webp`, `<slug>-scene-2.webp` and so on.
   - Place each scene in the body with `{% include scene.html n=1 %}` (n is its position in `scenes:`), on its own line, usually right after a `##` heading or between paragraphs, so a picture appears every few paragraphs. Put the includes at the same places in all five languages.
   - Write every `prompt` in English as a shot description for a film: who (a fictional person, age, clothing), the exact moment and action, the place, the time of day and the light (for example golden hour through a window, a cool blue train interior at dawn), the mood, and the framing (wide, mid-shot, close-up, over-the-shoulder, eye level or low angle). Vary the framing and light across the scenes, keep the same character consistent (repeat their description in every prompt) and make each scene a different moment. The workflow adds the cinematic house style, so don't describe the art style.
   - Keep prompts safe: no text in the image, no readable screens, no logos, no real or recognisable people, nothing that looks like a screenshot of the product.

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
7. **Preview image.** Set `image:` in the front matter of all five files to the `hero_image.src`, so search results and social shares use the illustration. Do not run `tools/render_previews.py` and do not create infographic PNGs; that script is retired.
8. **Check before publishing.** Run `python3 tools/check_post.py YYYY-MM-DD-<slug>.md`. It checks all five files against these rules (YAML parses, titles and descriptions, tags, the `ad` block, the FAQ, the date, the hero image and scenes, that every scene is included once, that shared values match across languages, and that nothing under `assets/img/` changed). Fix every problem it lists and run it again until it prints OK. Quote strings that contain a colon or a quote.
9. **Publish.** Commit the five post files (and nothing in `assets/img/`) to `main` with the message `post: <slug>`, then push. Never edit the layouts, includes, CSS, `_config.yml` (including the AdSense settings), `_data/`, `CNAME`, `tools/`, `.github/`, the search pages (`search.html` and `<code>/search.html`), `ads.txt`, `llms.txt`, `robots.txt`, the language home and author pages, or this file during a scheduled run. Never add ad code to a post; ads are placed by the layouts.
10. **Report.** End with the post title, the character, and the five live URLs: `https://blog.learningclarity.ai/<code>/YYYY/MM/<slug>/` for `en`, `ar`, `es`, `fr` and `de`. GitHub Pages takes about a minute to update; the images appear after the image workflow finishes, a few minutes later.
