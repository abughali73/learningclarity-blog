import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { asLang, BLOG_URL, COPY, db, EMAIL_RE, json, LANG_HOME, sendMail, sha256Hex, verifyEmailHtml } from "../_shared/blog.ts";

// POST {email, lang, hp, source} from the blog's subscribe form. Double opt-in: stores a pending
// subscriber and emails a confirmation link (blog-verify). The answer is the same whether or not the
// address is already on the list, so the form never reveals who is subscribed.
// verify_jwt=false: the blog has no Supabase session.

const RESEND_AFTER_MS = 10 * 60 * 1000;   // at most one confirmation email per address every 10 minutes
const MAX_SIGNUPS_PER_IP_HOUR = 5;

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return json(req, null, 204);
  if (req.method !== "POST") return json(req, { ok: false, error: "method" }, 405);

  let body: Record<string, unknown>;
  try {
    const text = await req.text();
    if (text.length > 2000) return json(req, { ok: false, error: "invalid" }, 400);
    body = JSON.parse(text);
  } catch {
    return json(req, { ok: false, error: "invalid" }, 400);
  }

  // Honeypot: real visitors never fill the hidden field. Pretend success.
  if (String(body.hp ?? "").trim()) return json(req, { ok: true });

  const email = String(body.email ?? "").trim().toLowerCase();
  if (!EMAIL_RE.test(email) || email.length > 254) return json(req, { ok: false, error: "email" }, 400);
  const lang = asLang(body.lang);
  const source = String(body.source ?? "").slice(0, 300) || null;

  const ip = (req.headers.get("x-forwarded-for") ?? "").split(",")[0].trim() || req.headers.get("x-real-ip") || "";
  const ipHash = ip ? (await sha256Hex(`blog-subscribe:${ip}:${new Date().toISOString().slice(0, 10)}`)).slice(0, 32) : null;

  const supabase = db();

  if (ipHash) {
    const { count } = await supabase.from("blog_subscribers").select("id", { count: "exact", head: true })
      .eq("signup_ip_hash", ipHash).gte("updated_at", new Date(Date.now() - 3600_000).toISOString());
    if ((count ?? 0) >= MAX_SIGNUPS_PER_IP_HOUR) return json(req, { ok: false, error: "rate" }, 429);
  }

  const { data: existing, error: readErr } = await supabase.from("blog_subscribers")
    .select("id, status, verify_token, verify_sent_at").eq("email", email).maybeSingle();
  if (readErr) {
    console.error("blog-subscribe read:", readErr.message);
    return json(req, { ok: false, error: "server" }, 500);
  }

  // Already confirmed: nothing to do, same answer as a new sign-up.
  if (existing?.status === "active") return json(req, { ok: true });

  if (existing?.verify_sent_at && Date.now() - Date.parse(existing.verify_sent_at) < RESEND_AFTER_MS) {
    return json(req, { ok: true });
  }

  const token = crypto.randomUUID();
  const row = {
    email, lang, status: "pending", verify_token: token, verify_sent_at: new Date().toISOString(),
    signup_source: source, signup_ip_hash: ipHash, updated_at: new Date().toISOString(),
    unsubscribed_at: null,
  };
  const { error: writeErr } = existing
    ? await supabase.from("blog_subscribers").update(row).eq("id", existing.id)
    : await supabase.from("blog_subscribers").insert(row);
  if (writeErr) {
    console.error("blog-subscribe write:", writeErr.message);
    return json(req, { ok: false, error: "server" }, 500);
  }

  // The link opens the blog page, which confirms only on a click (see blog-verify): link scanners can't confirm.
  const verifyUrl = `${BLOG_URL}${LANG_HOME[lang]}subscribed/?t=${token}`;
  const err = await sendMail({
    to: email,
    subject: COPY[lang].verifySubject,
    html: verifyEmailHtml(lang, verifyUrl),
    ref: `blog-verify:${token}`,
  });
  if (err) {
    console.error("blog-subscribe mail:", err);
    // Let the visitor try again straight away.
    await supabase.from("blog_subscribers").update({ verify_sent_at: null }).eq("email", email);
    return json(req, { ok: false, error: "mail" }, 502);
  }
  return json(req, { ok: true });
});
