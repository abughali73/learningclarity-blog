# Blog email subscription (Supabase Edge Functions)

Deployed to the **Learning_Clarity_Production** Supabase project (`xlkexogyodwnblladuvj`), all with `verify_jwt = false`.
Jekyll ignores this folder (`exclude:` in `_config.yml`).

| Function | Called by | Does |
|---|---|---|
| `blog-subscribe` | the subscribe box on every blog page | stores a pending subscriber and emails a confirmation link (double opt-in) |
| `blog-verify` | the link in the confirmation email | activates the subscriber, redirects to `/<lang>/subscribed/` |
| `blog-unsubscribe` | the form on `/<lang>/unsubscribe/?t=…` (linked from every new-post email) | unsubscribes, saves the reason in `blog_unsubscribe_feedback` and appends it to `unsubscribe_feedback.csv` (private Storage bucket `blog-feedback`) |
| `blog-notify` | the database job `blog-notify-subscribers__every_15m` (pg_cron, at :07, :22, :37 and :52), header `x-notify-secret` | emails active subscribers about new posts listed in `/subscribe-feed.json`, in their language |

Mail goes through Microsoft Graph (`/users/learningclarity.ai@intellisys.sk/sendMail`) with the project secrets the
app already uses: `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET` (optional `MS_SENDER_EMAIL`).

Tables (RLS on, no policies; only the functions' service role reads them): `blog_subscribers`, `blog_notified_posts`,
`blog_post_deliveries`, `blog_unsubscribe_feedback`, `blog_settings` (`notify_secret`, which the
pg_cron job reads directly, so the secret never leaves the database).

Deploy a function: `supabase functions deploy blog-notify --project-ref xlkexogyodwnblladuvj --no-verify-jwt`
(each function imports `../_shared/blog.ts`).

Send a test new-post email (only the sender mailbox is accepted), from the SQL editor:
`select net.http_post(url:='https://xlkexogyodwnblladuvj.supabase.co/functions/v1/blog-notify', body:='{"test_to":"learningclarity.ai@intellisys.sk","lang":"en"}'::jsonb, headers:=jsonb_build_object('content-type','application/json','x-notify-secret',(select value from blog_settings where key='notify_secret')));`
