import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { asLang, BLOG_URL, db, LANG_HOME, UUID_RE } from "../_shared/blog.ts";

// GET ?t=<verify_token> from the confirmation email. Activates the subscriber and redirects to the
// blog's "subscribed" page in their language (?status=invalid when the link is unknown or expired).
// verify_jwt=false: opened from an email.

const LINK_TTL_MS = 7 * 24 * 3600 * 1000;

const redirect = (lang: string, status?: string) =>
  new Response(null, {
    status: 303,
    headers: { Location: `${BLOG_URL}${LANG_HOME[asLang(lang)]}subscribed/${status ? `?status=${status}` : ""}` },
  });

Deno.serve(async (req: Request) => {
  if (req.method !== "GET") return new Response("Method not allowed", { status: 405 });
  const token = new URL(req.url).searchParams.get("t") ?? "";
  if (!UUID_RE.test(token)) return redirect("en", "invalid");

  const supabase = db();
  const { data: sub, error } = await supabase.from("blog_subscribers")
    .select("id, lang, status, verify_sent_at").eq("verify_token", token).maybeSingle();
  if (error) {
    console.error("blog-verify read:", error.message);
    return redirect("en", "error");
  }
  if (!sub) return redirect("en", "invalid");
  if (sub.status === "active") return redirect(sub.lang);
  if (!sub.verify_sent_at || Date.now() - Date.parse(sub.verify_sent_at) > LINK_TTL_MS) {
    return redirect(sub.lang, "invalid");
  }

  const now = new Date().toISOString();
  const { error: upErr } = await supabase.from("blog_subscribers")
    .update({ status: "active", verified_at: now, updated_at: now })
    .eq("id", sub.id);
  if (upErr) {
    console.error("blog-verify update:", upErr.message);
    return redirect(sub.lang, "error");
  }
  return redirect(sub.lang);
});
