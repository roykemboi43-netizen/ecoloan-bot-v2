import os
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

BOT_TOKEN = os.environ["BOT_TOKEN"]          # no fallback!
ADMIN_ID = os.environ["ADMIN_ID"]
WEBHOOK_PATH = f"/telegram/{BOT_TOKEN}"     # secret path
WEBHOOK_URL = f"https://site--ecoloan--8z6qccsrdhyw.code.run{WEBHOOK_PATH}"

# ... your database setup stays the same ...

web_app = FastAPI()
telegram_app: Application = None

# ---------- Telegram handlers (same as before) ----------
# (keep all your start, loan_start, get_name, etc. functions)

async def run_bot():
    global telegram_app
    telegram_app = (
        Application.builder()
        .token(BOT_TOKEN)
        .updater(None)          # we don't need the updater for webhooks
        .build()
    )

    # register handlers exactly as you already do
    loan_handler = ConversationHandler(...)
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(loan_handler)

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(
        url=WEBHOOK_URL,
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"]
    )
    print("Webhook set successfully")

@web_app.on_event("startup")
async def startup():
    await run_bot()

@web_app.on_event("shutdown")
async def shutdown():
    if telegram_app:
        await telegram_app.bot.delete_webhook()
        await telegram_app.stop()
        await telegram_app.shutdown()

@web_app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return Response(status_code=200)

# keep your / , /verify , /website-lead , /verify-code routes

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(web_app, host="0.0.0.0", port=port)
