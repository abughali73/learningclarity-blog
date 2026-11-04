import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import {
  asLang, BLOG_URL, db, json, mailProblem, Lang, newPostEmailHtml, PostInfo, sendMail, senderMailbox, sleep,
  unsubscribeUrl, UUID_RE,
} from "../_shared/blog.ts";

// Emails active subscribers about newly published blog posts, in their language.
// Called every 15 minutes by the database job blog-notify-subscribers__every_15m (pg_cron + pg_net)
// with header x-notify-secret = blog_settings.notify_secret. verify_jwt=false; the secret is the auth.
//
// The blog publishes /subscribe-feed.json (newest posts per language). A post seen for the first time is
// recorded in blog_notified_posts and mailed to every active subscriber of its language who confirmed
// before it appeared; each send is recorded in blog_post_deliveries, so a run that stops halfway resumes
// on the next call without sending anything twice. On the very first run every post already on the blog
// is recorded as "seeded" so nobody receives a backlog.
//
// Body (optional): {"test_to": "<address>", "lang": "en"} sends the newest post to that address only;
// allowed only for the sender mailbox itself, to check the email's look.

const TIME_BUDGET_MS = 100_000;     // stay well inside the edge function wall clock; the workflow calls again
const SEND_GAP_MS = 2_200;          // ~27 a minute: the sender mailbox allows 30 a minute, shared with the app
const MAX_POST_AGE_MS = 3 * 24 * 3600 * 1000;   // never announce a post older than this
const WAIT_FOR_IMAGE_MS = 6 * 3600 * 1000;      // hold a post up to 6 h for its picture, then send without it

interface FeedPost { url: string; ref: string; lang: string; title: string; description: string; eyebrow?: string; image?: string; date: string }

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

async function imageOk(url?: string): Promise<boolean> {
  if (!url) return false;
  try {
    const res = await fetch(url, { method: "HEAD" });
    return res.ok;
  } catch {
    return false;
  }
}

const info = (p: FeedPost, image: string | null): PostInfo =>
  ({ url: p.url, title: p.title, description: p.description, image, eyebrow: p.eyebrow });

Deno.serve(async (req: Request) => {
  const started = Date.now();
  if (req.method !== "POST") return json(req, { ok: false, error: "method" }, 405);

  const supabase = db();
  const { data: secretRow } = await supabase.from("blog_settings").select("value").eq("key", "notify_secret").maybeSingle();
  const given = req.headers.get("x-notify-secret") ?? "";
  if (!secretRow?.value || !timingSafeEqual(given, secretRow.value)) return json(req, { ok: false, error: "auth" }, 401);

  const problem = mailProblem();
  if (problem) return json(req, { ok: false, error: problem }, 500);

  let body: Record<string, unknown> = {};
  try { body = await req.json(); } catch { /* empty body is fine */ }

  const feedRes = await fetch(`${BLOG_URL}/subscribe-feed.json?v=${Date.now()}`);
  if (!feedRes.ok) return json(req, { ok: false, error: `feed ${feedRes.status}` }, 502);
  const feed = ((await feedRes.json()).posts ?? []) as FeedPost[];
  const byUrl = new Map(feed.map((p) => [p.url, p]));

  // ---- Test send to the sender mailbox only ---------------------------------------------------
  if (body.test_to) {
    const to = String(body.test_to).trim().toLowerCase();
    if (to !== senderMailbox().toLowerCase()) return json(req, { ok: false, error: "test_to must be the sender mailbox" }, 400);
    const lang = asLang(body.lang);
    const post = feed.find((p) => p.lang === lang);
    if (!post) return json(req, { ok: false, error: "no post" }, 404);
    const { data: sub } = await supabase.from("blog_subscribers").select("unsubscribe_token").eq("email", to).maybeSingle();
    const token = sub?.unsubscribe_token ?? "00000000-0000-4000-8000-000000000000";
    const image = (await imageOk(post.image)) ? post.image! : null;
    const err = await sendMail({ to, subject: post.title, html: newPostEmailHtml(lang, info(post, image), unsubscribeUrl(lang, token)), ref: `blog-test:${post.ref}`, unsubscribeUrl: unsubscribeUrl(lang, token) });
    return json(req, { ok: !err, test: true, post: post.url, error: err });
  }

  // ---- First run: record what is already published, send nothing ----------------------------
  const { count: known } = await supabase.from("blog_notified_posts").select("url", { count: "exact", head: true });
  if (!known) {
    const rows = feed.map((p) => ({ url: p.url, ref: p.ref, lang: p.lang, title: p.title, status: "seeded", completed_at: new Date().toISOString() }));
    const { error } = await supabase.from("blog_notified_posts").upsert(rows, { onConflict: "url", ignoreDuplicates: true });
    if (error) return json(req, { ok: false, error: error.message }, 500);
    return json(req, { ok: true, seeded: rows.length, sent: 0, remaining: false });
  }

  // ---- Record newly published posts ------------------------------------------------------------
  const { data: knownRows } = await supabase.from("blog_notified_posts").select("url").in("url", feed.map((p) => p.url));
  const knownSet = new Set((knownRows ?? []).map((r) => r.url));
  const held: string[] = [];
  for (const p of feed) {
    if (knownSet.has(p.url)) continue;
    const age = Date.now() - Date.parse(p.date);
    if (!(age < MAX_POST_AGE_MS)) {
      // Too old to announce (or undated): remember it so it is never sent.
      await supabase.from("blog_notified_posts").upsert({ url: p.url, ref: p.ref, lang: p.lang, title: p.title, status: "seeded", completed_at: new Date().toISOString() }, { onConflict: "url", ignoreDuplicates: true });
      continue;
    }
    if (!(await imageOk(p.image)) && age < WAIT_FOR_IMAGE_MS) { held.push(p.url); continue; }
    await supabase.from("blog_notified_posts").upsert({ url: p.url, ref: p.ref, lang: p.lang, title: p.title, status: "sending" }, { onConflict: "url", ignoreDuplicates: true });
  }

  // ---- Send ------------------------------------------------------------------------------------
  const { data: sending } = await supabase.from("blog_notified_posts").select("url, lang, first_seen_at").eq("status", "sending").order("first_seen_at");
  let sent = 0, failed = 0, remaining = false;
  const errors: string[] = [];

  for (const row of sending ?? []) {
    const post = byUrl.get(row.url);
    const lang = asLang(row.lang) as Lang;
    if (!post) {
      // Taken down or out of the feed window: stop announcing it.
      await supabase.from("blog_notified_posts").update({ status: "done", completed_at: new Date().toISOString() }).eq("url", row.url);
      continue;
    }
    const image = (await imageOk(post.image)) ? post.image! : null;

    const { data: subs } = await supabase.from("blog_subscribers").select("id, email, unsubscribe_token")
      .eq("status", "active").eq("lang", lang).lte("verified_at", row.first_seen_at);
    const { data: done } = await supabase.from("blog_post_deliveries").select("subscriber_id").eq("post_url", row.url);
    const doneSet = new Set((done ?? []).map((d) => d.subscriber_id));
    const todo = (subs ?? []).filter((s) => !doneSet.has(s.id) && UUID_RE.test(s.unsubscribe_token));

    for (const s of todo) {
      if (Date.now() - started > TIME_BUDGET_MS) { remaining = true; break; }
      const err = await sendMail({
        to: s.email,
        subject: post.title,
        html: newPostEmailHtml(lang, info(post, image), unsubscribeUrl(lang, s.unsubscribe_token)),
        ref: `blog-post:${post.ref}:${lang}:${s.id}`,
        unsubscribeUrl: unsubscribeUrl(lang, s.unsubscribe_token),
      });
      if (err && /^(Mail not configured|Graph token|Graph (401|403|5\d\d)|Graph retry)/.test(err)) {
        // A problem with the sender, not this address: stop, record nothing, and retry on the next run.
        errors.push(err); remaining = true; break;
      }
      // A failed send for one address is recorded, so a bad address cannot block the rest or be retried forever.
      await supabase.from("blog_post_deliveries").upsert({ post_url: row.url, subscriber_id: s.id, outcome: err ? "failed" : "accepted", error: err }, { onConflict: "post_url,subscriber_id" });
      if (err) { failed++; if (errors.length < 5) errors.push(err); } else sent++;
      await sleep(SEND_GAP_MS);
    }
    if (remaining) break;
    await supabase.from("blog_notified_posts").update({ status: "done", completed_at: new Date().toISOString() }).eq("url", row.url);
  }

  return json(req, { ok: true, sent, failed, remaining, held, errors });
});
