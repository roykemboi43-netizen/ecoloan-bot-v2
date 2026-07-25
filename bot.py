import os
import sqlite3
from datetime import datetime
from contextlib import asynccontextmanager

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ======================
# CONFIG
# ======================
BOT_TOKEN = os.environ["BOT_TOKEN"]          # must be set in Northflank Secrets
ADMIN_ID = os.environ["ADMIN_ID"]            # must be set in Northflank Secrets
LOAN_LINK = "https://ecoloanstrustedagent.netlify.app/"
VERIFY_LINK = "https://ecoloanstrustedagent.netlify.app/verify"

# Public URL of this Northflank service
BASE_URL = "https://site--ecoloan--8z6qccsrdhyw.code.run"
WEBHOOK_PATH = f"/telegram/{BOT_TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

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
# TELEGRAM HANDLERS
# ======================
NAME, EMAIL, PHONE, OCCUPATION, STATUS, LOAN_USAGE = range(6)

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
    await update.message.reply_text(
        "Status? (Employed / Self Employed / Student / Unemployed)"
    )
    return STATUS

async def get_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["status"] = update.message.text
    await update.message.reply_text("What will you use the loan for?")
    return LOAN_USAGE

async def get_loan_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["loan_usage"] = update.message.text
    user_id = str(update.effective_user
