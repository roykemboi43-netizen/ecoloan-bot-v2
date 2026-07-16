import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

# ======================
# CONFIG
# ======================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8647388636:AAG_Fhp1JMwHdoKH_hCyADrcaPuoRh4QtXI")
ADMIN_ID = os.environ.get("ADMIN_ID", "5887256773")
LOAN_LINK = "https://ecoloanstrustedagent.netlify.app/"
VERIFY_LINK = "https://ecoloan-bot-v2-production.up.railway.app/website-lead"

# ======================
# DATABASE
# ======================
conn = sqlite3.connect("loan_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS applications (...)""")  # keep your table creations
cursor.execute("""CREATE TABLE IF NOT EXISTS website_leads (...)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS verifications (...)""")
try:
    cursor.execute("ALTER TABLE applications ADD COLUMN source TEXT DEFAULT 'telegram'")
except:
    pass
conn.commit()

# ======================
# FastAPI
# ======================
web_app = FastAPI()
web_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

@web_app.get("/")
async def serve_home():
    with open("index.html", "r") as f:
        return HTMLResponse(content=f.read())

@web_app.get("/verify")
async def serve_verify():
    with open("verify.html", "r") as f:
        return HTMLResponse(content=f.read())

@web_app.get("/health")
async def health():
    return {"status": "running"}

@web_app.post("/website-lead")
async def website_lead(request: Request):
    try:
        data = await request.json()
        name = data.get("name", "N/A")
        email = data.get("email", "N/A")
        phone = data.get("phone", "N/A")
        amount = data.get("amount", "Not specified")
        message = data.get("message", "No message")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""INSERT INTO website_leads ...""", (name, email, phone, amount, message, timestamp))
        conn.commit()

        admin_msg = f"NEW WEBSITE LOAN APPLICATION\n\nName: {name}\nEmail: {email}\n..."
        await telegram_app.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)

        return JSONResponse({"status": "success", "message": "Thank you!"})
    except Exception as e:
        print("Website error:", e)
        raise HTTPException(status_code=400, detail="Error")

# ======================
# TELEGRAM BOT
# ======================
NAME, EMAIL, PHONE, OCCUPATION, STATUS, LOAN_USAGE = range(6)
telegram_app = None

# Your handler functions (start, loan_start, get_name, etc.) — keep them exactly as you have

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to EcoLoan Assistant!\n\nUse /loan to start your application.")

# ... (keep all your other handlers: get_name, get_email, etc.)

# ======================
# MAIN
# ======================
async def main():
    global telegram_app
    
    telegram_app = Application.builder().token(BOT_TOKEN).build()

    loan_handler = ConversationHandler(
        entry_points=[CommandHandler("loan", loan_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            OCCUPATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_occupation)],
            STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_status)],
            LOAN_USAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_loan_usage)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(loan_handler)

    await telegram_app.initialize()
    await telegram_app.start()
    
    # Improved polling for Railway
    await telegram_app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"]
    )
    
    print("✅ EcoLoan Bot is polling...")

    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting web server on port {port}")
    
    # Run FastAPI + Bot together
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start bot in background
    loop.create_task(main())
    
    uvicorn.run(web_app, host="0.0.0.0", port=port)
