import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { db, json, UUID_RE } from "../_shared/blog.ts";

// POST {token, reason, comment} from the blog's unsubscribe page (the link in every new-post email).
// Unsubscribes the address, stores the feedback in blog_unsubscribe_feedback and appends it to
// unsubscribe_feedback.csv in the private Storage bucket "blog-feedback".
// verify_jwt=false: the blog has no Supabase session.

const REASONS = ["too_many", "not_relevant", "never_signed_up", "read_elsewhere", "other"];
const BUCKET = "blog-feedback";
const CSV_PATH = "unsubscribe_feedback.csv";
const CSV_HEADER = "submitted_at,email,language,reason,comment\n";
const BOM = "\uFEFF";   // so Excel opens the UTF-8 file (Arabic, accents) correctly

const csvCell = (v: unknown) => {
  let s = String(v ?? "").replace(/\r?\n/g, " ");
  if (/^[=+\-@\t]/.test(s)) s = "'" + s;          // keep spreadsheet apps from running it as a formula
  return /[",]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

async function appendCsv(supabase: ReturnType<typeof db>, line: string): Promise<void> {
  // Read-modify-write. Unsubscribes are rare, so a lost update is unlikely; the table keeps every row anyway.
  for (let attempt = 0; attempt < 2; attempt++) {
    let current = CSV_HEADER;
    const { data } = await supabase.storage.from(BUCKET).download(CSV_PATH);
    if (data) current = await data.text();
    if (!current.endsWith("\n")) current += "\n";
    const { error } = await supabase.storage.from(BUCKET).upload(
      CSV_PATH,
      new Blob([current.startsWith(BOM) ? current + line : BOM + current + line], { type: "text/csv; charset=utf-8" }),
      { upsert: true, contentType: "text/csv; charset=utf-8" },
    );
    if (!error) return;
    console.error("blog-unsubscribe csv:", error.message);
  }
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return json(req, null, 204);
  if (req.method !== "POST") return json(req, { ok: false, error: "method" }, 405);

  let body: Record<string, unknown>;
  try {
    const text = await req.text();
    if (text.length > 5000) return json(req, { ok: false, error: "invalid" }, 400);
    body = JSON.parse(text);
  } catch {
    return json(req, { ok: false, error: "invalid" }, 400);
  }

  const token = String(body.token ?? "");
  if (!UUID_RE.test(token)) return json(req, { ok: false, error: "token" }, 400);
  const reason = REASONS.includes(String(body.reason)) ? String(body.reason) : "other";
  const comment = String(body.comment ?? "").trim().slice(0, 1000) || null;

  const supabase = db();
  const { data: sub, error } = await supabase.from("blog_subscribers")
    .select("id, email, lang, status").eq("unsubscribe_token", token).maybeSingle();
  if (error) {
    console.error("blog-unsubscribe read:", error.message);
    return json(req, { ok: false, error: "server" }, 500);
  }
  if (!sub) return json(req, { ok: false, error: "token" }, 404);

  const now = new Date().toISOString();
  if (sub.status !== "unsubscribed") {
    const { error: upErr } = await supabase.from("blog_subscribers")
      .update({ status: "unsubscribed", unsubscribed_at: now, updated_at: now }).eq("id", sub.id);
    if (upErr) {
      console.error("blog-unsubscribe update:", upErr.message);
      return json(req, { ok: false, error: "server" }, 500);
    }
  }

  const { error: fbErr } = await supabase.from("blog_unsubscribe_feedback")
    .insert({ subscriber_id: sub.id, email: sub.email, lang: sub.lang, reason, comment });
  if (fbErr) console.error("blog-unsubscribe feedback:", fbErr.message);

  await appendCsv(supabase, [now, sub.email, sub.lang, reason, comment ?? ""].map(csvCell).join(",") + "\n");
  return json(req, { ok: true });
});
