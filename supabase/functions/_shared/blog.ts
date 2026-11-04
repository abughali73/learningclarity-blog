// Shared code for the blog email subscription functions (blog-subscribe, blog-verify,
// blog-unsubscribe, blog-notify). Source of truth: the learningclarity-blog repo, supabase/functions/.
//
// Mail goes out through Microsoft Graph from the app's sender mailbox, learningclarity.ai@intellisys.sk,
// with the same client-credentials secrets the app's own emails use (MS_TENANT_ID, MS_CLIENT_ID,
// MS_CLIENT_SECRET; MS_SENDER_EMAIL optionally overrides the mailbox). That mailbox allows about
// 30 messages a minute, shared with the app, so senders here pace themselves.

import { createClient, SupabaseClient } from "jsr:@supabase/supabase-js@2";

export const BLOG_URL = "https://blog.learningclarity.ai";
export const LANGS = ["en", "ar", "es", "fr", "de"] as const;
export type Lang = typeof LANGS[number];
export const LANG_HOME: Record<Lang, string> = { en: "/", ar: "/ar/", es: "/es/", fr: "/fr/", de: "/de/" };
export const asLang = (v: unknown): Lang => (LANGS as readonly string[]).includes(String(v)) ? v as Lang : "en";

const ALLOWED_ORIGINS = [BLOG_URL, "http://localhost:4000", "http://127.0.0.1:4000"];

export function corsHeaders(req: Request): Record<string, string> {
  const origin = req.headers.get("origin") ?? "";
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGINS.includes(origin) ? origin : BLOG_URL,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

export function json(req: Request, body: unknown, status = 200): Response {
  // 204/304 must not carry a body (Deno throws), e.g. the CORS preflight answer.
  if (status === 204 || status === 304) return new Response(null, { status, headers: corsHeaders(req) });
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders(req), "Content-Type": "application/json; charset=utf-8" },
  });
}

export function db(): SupabaseClient {
  return createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SB_SECRET_KEY") ?? Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { persistSession: false } },
  );
}

export const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export const EMAIL_RE = /^[^\s@<>()",;:]{1,64}@[a-z0-9-]+(\.[a-z0-9-]+)+$/i;

export async function sha256Hex(text: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function esc(s: string): string {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

// ---- Microsoft Graph -------------------------------------------------------------------------

let tokenCache: { token: string; exp: number } | null = null;

export function graphProblem(): string | null {
  const missing = ["MS_TENANT_ID", "MS_CLIENT_ID", "MS_CLIENT_SECRET"].filter((k) => !Deno.env.get(k));
  return missing.length ? `Graph mail not configured: missing ${missing.join(", ")}` : null;
}

export function senderMailbox(): string {
  return (Deno.env.get("MS_SENDER_EMAIL") ?? "").trim() || "learningclarity.ai@intellisys.sk";
}

async function fetchT(url: string, init: RequestInit, ms: number): Promise<Response> {
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), ms);
  try { return await fetch(url, { ...init, signal: c.signal }); } finally { clearTimeout(t); }
}

async function graphToken(): Promise<string> {
  if (tokenCache && tokenCache.exp > Date.now()) return tokenCache.token;
  const tenant = Deno.env.get("MS_TENANT_ID")!;
  const res = await fetchT(`https://login.microsoftonline.com/${encodeURIComponent(tenant)}/oauth2/v2.0/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "client_credentials",
      client_id: Deno.env.get("MS_CLIENT_ID")!,
      client_secret: Deno.env.get("MS_CLIENT_SECRET")!,
      scope: "https://graph.microsoft.com/.default",
    }).toString(),
  }, 10_000);
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.access_token) {
    throw new Error(`Graph token refused (${res.status}): ${String(data.error ?? "")} ${String(data.error_description ?? "").split("\n")[0]}`.slice(0, 300));
  }
  tokenCache = { token: data.access_token, exp: Date.now() + (Number(data.expires_in ?? 3599) - 300) * 1000 };
  return tokenCache.token;
}

export interface Mail { to: string; subject: string; html: string; ref: string }

/** Sends one message. Returns null when Graph accepted it, otherwise an error text. */
export async function sendMail(m: Mail): Promise<string | null> {
  const problem = graphProblem();
  if (problem) return problem;
  const mailbox = senderMailbox();
  const body = JSON.stringify({
    message: {
      subject: m.subject,
      body: { contentType: "HTML", content: m.html },
      from: { emailAddress: { address: mailbox, name: "Learning Clarity Blog" } },
      toRecipients: [{ emailAddress: { address: m.to } }],
      // Graph accepts only x- custom headers, so List-Unsubscribe cannot be set; the footer link is the opt-out.
      internetMessageHeaders: [{ name: "x-lc-message-ref", value: m.ref.slice(0, 200) }],
    },
    saveToSentItems: false,
  });
  for (let attempt = 0; attempt < 3; attempt++) {
    let token: string;
    try { token = await graphToken(); } catch (e) { return (e as Error).message; }
    let res: Response;
    try {
      res = await fetchT(`https://graph.microsoft.com/v1.0/users/${encodeURIComponent(mailbox)}/sendMail`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body,
      }, 20_000);
    } catch (e) {
      return `uncertain: no response from Graph (${(e as Error).message})`;
    }
    if (res.status === 202) return null;
    const detail = (await res.text().catch(() => "")).slice(0, 300);
    if (res.status === 401) tokenCache = null;
    if ((res.status === 429 || res.status === 503) && attempt < 2) {
      const wait = Math.min(Number(res.headers.get("retry-after") ?? "5") || 5, 20);
      await sleep(wait * 1000);
      continue;
    }
    return `Graph ${res.status}: ${detail}`;
  }
  return "Graph retry exhausted";
}

// ---- Email copy ------------------------------------------------------------------------------

interface Copy {
  rtl: boolean;
  verifySubject: string;
  verifyHeading: string;
  verifyIntro: string;
  verifyButton: string;
  verifyIgnore: string;
  newPostEyebrow: string;
  readButton: string;
  whyReceiving: string;
  unsubscribe: string;
  team: string;
  ownership: string;
}

const OWNER = "intelliSYS Solutions &amp; Consulting LLC";

export const COPY: Record<Lang, Copy> = {
  en: {
    rtl: false,
    verifySubject: "Confirm your subscription to the Learning Clarity Blog",
    verifyHeading: "One click to confirm",
    verifyIntro: "Thanks for subscribing to the Learning Clarity Blog. Please confirm your email address, and we'll let you know whenever a new post is published.",
    verifyButton: "Confirm my subscription",
    verifyIgnore: "Didn't ask for this? Just ignore this email and you won't be subscribed.",
    newPostEyebrow: "New on the Learning Clarity Blog",
    readButton: "Read the post",
    whyReceiving: "You're receiving this because you subscribed to new posts on the Learning Clarity Blog.",
    unsubscribe: "Unsubscribe",
    team: "The Learning Clarity Team",
    ownership: `learningclarity.ai is a product owned by ${OWNER}.`,
  },
  ar: {
    rtl: true,
    verifySubject: "أكِّد اشتراكك في مدونة Learning Clarity",
    verifyHeading: "نقرة واحدة للتأكيد",
    verifyIntro: "شكرًا لاشتراكك في مدونة Learning Clarity. يُرجى تأكيد بريدك الإلكتروني، وسنُعلمك كلما نُشر مقال جديد.",
    verifyButton: "تأكيد اشتراكي",
    verifyIgnore: "لم تطلب ذلك؟ تجاهل هذه الرسالة ولن يتم اشتراكك.",
    newPostEyebrow: "جديد في مدونة Learning Clarity",
    readButton: "اقرأ المقال",
    whyReceiving: "تصلك هذه الرسالة لأنك اشتركت في إشعارات المقالات الجديدة في مدونة Learning Clarity.",
    unsubscribe: "إلغاء الاشتراك",
    team: "فريق Learning Clarity",
    ownership: `learningclarity.ai منتج مملوك لشركة ${OWNER}.`,
  },
  es: {
    rtl: false,
    verifySubject: "Confirma tu suscripción al blog de Learning Clarity",
    verifyHeading: "Un clic para confirmar",
    verifyIntro: "Gracias por suscribirte al blog de Learning Clarity. Confirma tu dirección de correo y te avisaremos cada vez que publiquemos un artículo nuevo.",
    verifyButton: "Confirmar mi suscripción",
    verifyIgnore: "¿No lo has pedido tú? Ignora este correo y no quedarás suscrito.",
    newPostEyebrow: "Nuevo en el blog de Learning Clarity",
    readButton: "Leer el artículo",
    whyReceiving: "Recibes este correo porque te suscribiste a los nuevos artículos del blog de Learning Clarity.",
    unsubscribe: "Darse de baja",
    team: "El equipo de Learning Clarity",
    ownership: `learningclarity.ai es un producto propiedad de ${OWNER}.`,
  },
  fr: {
    rtl: false,
    verifySubject: "Confirmez votre abonnement au blog Learning Clarity",
    verifyHeading: "Un clic pour confirmer",
    verifyIntro: "Merci de vous être abonné au blog Learning Clarity. Confirmez votre adresse e-mail et nous vous préviendrons à chaque nouvel article.",
    verifyButton: "Confirmer mon abonnement",
    verifyIgnore: "Vous n'avez rien demandé ? Ignorez simplement cet e-mail : vous ne serez pas abonné.",
    newPostEyebrow: "Nouveau sur le blog Learning Clarity",
    readButton: "Lire l'article",
    whyReceiving: "Vous recevez cet e-mail car vous vous êtes abonné aux nouveaux articles du blog Learning Clarity.",
    unsubscribe: "Se désabonner",
    team: "L'équipe Learning Clarity",
    ownership: `learningclarity.ai est un produit appartenant à ${OWNER}.`,
  },
  de: {
    rtl: false,
    verifySubject: "Bitte bestätigen Sie Ihr Abonnement des Learning Clarity Blogs",
    verifyHeading: "Ein Klick zur Bestätigung",
    verifyIntro: "Vielen Dank, dass Sie den Learning Clarity Blog abonniert haben. Bitte bestätigen Sie Ihre E-Mail-Adresse, dann informieren wir Sie über jeden neuen Beitrag.",
    verifyButton: "Abonnement bestätigen",
    verifyIgnore: "Sie haben das nicht angefordert? Dann ignorieren Sie diese E-Mail einfach, und Sie werden nicht angemeldet.",
    newPostEyebrow: "Neu im Learning Clarity Blog",
    readButton: "Beitrag lesen",
    whyReceiving: "Sie erhalten diese E-Mail, weil Sie neue Beiträge des Learning Clarity Blogs abonniert haben.",
    unsubscribe: "Abmelden",
    team: "Das Learning Clarity Team",
    ownership: `learningclarity.ai ist ein Produkt im Besitz der ${OWNER}.`,
  },
};

function shell(lang: Lang, inner: string, footer: string): string {
  const c = COPY[lang];
  const dir = c.rtl ? "rtl" : "ltr";
  const font = c.rtl ? "Tahoma,Arial,Helvetica,sans-serif" : "Arial,Helvetica,sans-serif";
  return `<!DOCTYPE html>
<html lang="${lang}" dir="${dir}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Learning Clarity</title></head>
<body style="margin:0;padding:0;background-color:#f0f9ff;font-family:${font};">
<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f0f9ff" style="background-color:#f0f9ff;"><tr><td align="center" style="padding:32px 12px;">
<table width="560" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;width:100%;border:1px solid #e2e8f0;background-color:#ffffff;">
<tr><td align="center" bgcolor="#2563eb" style="padding:22px 32px;background-color:#2563eb;background:linear-gradient(to right,#2563eb,#0891b2,#0284c7);">
<span style="display:block;font-size:20px;font-weight:700;color:#ffffff;font-family:${font};">Learning <span style="color:#bae6fd;">Clarity</span></span>
<span style="display:block;font-size:12px;font-weight:700;color:#bae6fd;text-transform:uppercase;letter-spacing:2px;font-family:${font};margin-top:4px;">Blog</span>
</td></tr>
${inner}
<tr><td align="center" bgcolor="#f8fafc" style="padding:20px 32px;background-color:#f8fafc;border-top:1px solid #e2e8f0;font-family:${font};">
<p style="margin:0 0 4px;font-size:13px;font-weight:700;color:#334155;">${esc(c.team)}</p>
<p style="margin:0 0 12px;font-size:12px;color:#64748b;"><a href="${BLOG_URL}${LANG_HOME[lang]}" style="color:#64748b;">blog.learningclarity.ai</a></p>
${footer}
<p style="margin:8px 0 0;font-size:11px;color:#94a3b8;">${c.ownership.replace("learningclarity.ai", "<bdi>learningclarity.ai</bdi>")}</p>
</td></tr></table></td></tr></table></body></html>`;
}

export function verifyEmailHtml(lang: Lang, verifyUrl: string): string {
  const c = COPY[lang];
  const align = c.rtl ? "right" : "left";
  const inner = `<tr><td style="padding:32px;text-align:${align};">
<h1 style="margin:0 0 14px;font-size:22px;color:#0f172a;">${esc(c.verifyHeading)}</h1>
<p style="margin:0 0 26px;font-size:15px;line-height:1.65;color:#334155;">${esc(c.verifyIntro)}</p>
<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center">
<a href="${esc(verifyUrl)}" style="display:inline-block;background-color:#2563eb;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;padding:13px 32px;border-radius:8px;">${esc(c.verifyButton)}</a>
</td></tr></table>
<p style="margin:26px 0 0;font-size:13px;line-height:1.6;color:#64748b;">${esc(c.verifyIgnore)}</p>
</td></tr>`;
  return shell(lang, inner, "");
}

export interface PostInfo { url: string; title: string; description: string; image: string | null; eyebrow?: string }

export function newPostEmailHtml(lang: Lang, post: PostInfo, unsubscribeUrl: string): string {
  const c = COPY[lang];
  const align = c.rtl ? "right" : "left";
  const img = post.image
    ? `<tr><td style="padding:0;"><a href="${esc(post.url)}"><img src="${esc(post.image)}" width="560" alt="" style="display:block;width:100%;max-width:560px;height:auto;border:0;"></a></td></tr>`
    : "";
  const inner = `${img}<tr><td style="padding:28px 32px;text-align:${align};">
<p style="margin:0 0 8px;font-size:12px;font-weight:700;color:#0891b2;text-transform:uppercase;letter-spacing:1px;">${esc(post.eyebrow || c.newPostEyebrow)}</p>
<h1 style="margin:0 0 12px;font-size:22px;line-height:1.3;color:#0f172a;"><a href="${esc(post.url)}" style="color:#0f172a;text-decoration:none;">${esc(post.title)}</a></h1>
<p style="margin:0 0 24px;font-size:15px;line-height:1.65;color:#334155;">${esc(post.description)}</p>
<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="${align}">
<a href="${esc(post.url)}" style="display:inline-block;background-color:#2563eb;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;padding:13px 32px;border-radius:8px;">${esc(c.readButton)}</a>
</td></tr></table>
</td></tr>`;
  const footer = `<p style="margin:0 0 12px;font-size:11px;line-height:1.5;color:#94a3b8;">${esc(c.whyReceiving)}</p>
<a href="${esc(unsubscribeUrl)}" style="display:inline-block;border:1px solid #cbd5e1;color:#475569;font-size:12px;font-weight:700;text-decoration:none;padding:7px 18px;border-radius:6px;">${esc(c.unsubscribe)}</a>`;
  return shell(lang, inner, footer);
}

export function unsubscribeUrl(lang: Lang, token: string): string {
  return `${BLOG_URL}${LANG_HOME[lang]}unsubscribe/?t=${token}`;
}
