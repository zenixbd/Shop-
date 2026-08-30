"""
Configuration module for Telegram Digital Product Shop Bot.
Loads environment variables and sets core constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()

# Telegram Settings
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0").strip()
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0
BOT_USERNAME = os.getenv("BOT_USERNAME", "DigitalShopBot").strip().replace("@", "")

# Bohudur Payment Gateway Settings
BOHUDUR_API_BASE_URL = os.getenv("BOHUDUR_API_BASE_URL", "https://api.bohudur.com/v1").rstrip("/")
BOHUDUR_API_KEY = os.getenv("BOHUDUR_API_KEY", "").strip()
BOHUDUR_API_SECRET = os.getenv("BOHUDUR_API_SECRET", "").strip()
BOHUDUR_MERCHANT_ID = os.getenv("BOHUDUR_MERCHANT_ID", "").strip()
BOHUDUR_WEBHOOK_SECRET = os.getenv("BOHUDUR_WEBHOOK_SECRET", "").strip()

# Webhook & Server Settings
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5000"))
RUN_MODE = os.getenv("RUN_MODE", "polling").lower()

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "shop_bot.db"))

# Currency & Business Rules
CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL", "৳")
MIN_DEPOSIT = float(os.getenv("MIN_DEPOSIT", "10"))
MAX_DEPOSIT = float(os.getenv("MAX_DEPOSIT", "25000"))
REFERRAL_BONUS_PERCENT = float(os.getenv("REFERRAL_BONUS_PERCENT", "5.0"))
DAILY_FREE_SPIN = int(os.getenv("DAILY_FREE_SPIN", "1"))
SPIN_COST = float(os.getenv("SPIN_COST", "20.0"))

DELIVERY_TYPES = ["TEXT", "LICENSE_KEY", "CODE", "LINK", "FILE", "DOCUMENT", "IMAGE", "VIDEO"]
ORDER_STATUSES = ["PENDING", "PAID", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED", "REFUNDED"]
PAYMENT_STATUSES = ["PENDING", "SUCCESS", "FAILED", "CANCELLED", "EXPIRED"]
