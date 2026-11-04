import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { asLang, BLOG_URL, db, json, LANG_HOME, UUID_RE } from "../_shared/blog.ts";

// Confirms a subscription. The confirmation email links to the blog page /<lang>/subscribed/?t=<token>, and the
// subscription is only activated when the visitor clicks "Confirm" there (POST {token}). Email security scanners
// (e.g. Microsoft Safe Links) open links automatically, so a plain GET must never activate anything.
//   POST {token}  -> activates; {ok:true, lang} or {ok:false, error:"invalid"|"server"}
//   GET  ?t=      -> (links in older emails) redirects to the blog page, which asks for the click
// verify_jwt=false: called from the blog, which has no Supabase session.

const LINK_TTL_MS = 7 * 24 * 3600 * 1000;

const page = (lang: string, query: string) =>
  new Response(null, { status: 303, headers: { Location: `${BLOG_URL}${LANG_HOME[asLang(lang)]}subscribed/${query}` } });

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return json(req, null, 204);
  const supabase = db();

  if (req.method === "GET") {
    const token = new URL(req.url).searchParams.get("t") ?? "";
    if (!UUID_RE.test(token)) return page("en", "?status=invalid");
    const { data: sub } = await supabase.from("blog_subscribers").select("lang").eq("verify_token", token).maybeSingle();
    return page(sub?.lang ?? "en", `?t=${token}`);
  }
  if (req.method !== "POST") return json(req, { ok: false, error: "method" }, 405);

  let token = "";
  try { token = String((await req.json()).token ?? ""); } catch { /* invalid body */ }
  if (!UUID_RE.test(token)) return json(req, { ok: false, error: "invalid" }, 400);

  const { data: sub, error } = await supabase.from("blog_subscribers")
    .select("id, lang, status, verify_sent_at").eq("verify_token", token).maybeSingle();
  if (error) {
    console.error("blog-verify read:", error.message);
    return json(req, { ok: false, error: "server" }, 500);
  }
  if (!sub) return json(req, { ok: false, error: "invalid" }, 404);
  if (sub.status === "active") return json(req, { ok: true, lang: sub.lang });
  if (!sub.verify_sent_at || Date.now() - Date.parse(sub.verify_sent_at) > LINK_TTL_MS) {
    return json(req, { ok: false, error: "invalid" }, 410);
  }

  const now = new Date().toISOString();
  const { error: upErr } = await supabase.from("blog_subscribers")
    .update({ status: "active", verified_at: now, updated_at: now }).eq("id", sub.id);
  if (upErr) {
    console.error("blog-verify update:", upErr.message);
    return json(req, { ok: false, error: "server" }, 500);
  }
  return json(req, { ok: true, lang: sub.lang });
});
