# Setup (about 30 minutes, all free, no coding)

1. **Render (hosts the website).** Sign up at render.com with GitHub > New > Blueprint > pick this repo > Apply.
   When it is live, copy the web address, then in Render > Environment set `PUBLIC_BASE_URL` to it, and set `SUPPORT_EMAIL` to your email.
2. **Paystack (takes payments).** Create a Paystack business account (Nigeria). Copy the *Secret key* (Settings > API Keys).
   Put it in Render as `PAYSTACK_SECRET_KEY`. Optional: set the webhook URL to `<your address>/webhook/paystack`.
   Until this key is set, the site shows the free checker only (no fake buy buttons).
3. **Gemini key (the writer).** Get a free key at aistudio.google.com. In GitHub: repo > Settings > Secrets and variables > Actions > New secret:
   `GEMINI_API_KEY`. Add the same `PUBLIC_BASE_URL`, `PAYSTACK_SECRET_KEY` as secrets so the CEO can read sales.
4. **Telegram report (optional).** Create a bot with @BotFather; add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as secrets.
5. **Start it.** GitHub > Actions > "Daily company cycle" > Run workflow. After that it runs by itself every day.

Free Render sites sleep after inactivity, so the first visit can take about 30 seconds to wake up. That is normal on the free plan.
