"""
Main Application Entry Point for Telegram Digital Product Shop Bot.
Boots the SQLite database, registers all user and admin message/callback handlers,
starts the Bohudur webhook server in a background thread, and executes resilient polling.
"""

import sys
import threading
import time
from telebot import TeleBot
from config import BOT_TOKEN, WEBHOOK_HOST, WEBHOOK_PORT, RUN_MODE
from database import init_database
from services.notification_service import notification_service
from web.webhook import app as flask_app

# Import all handler registration functions
from handlers.start import register_start_handlers
from handlers.shop import register_shop_handlers
from handlers.products import register_product_handlers
from handlers.orders import register_orders_handlers
from handlers.profile import register_profile_handlers
from handlers.wallet import register_wallet_handlers
from handlers.payments import register_payments_handlers
from handlers.referral import register_referral_handlers
from handlers.spin import register_spin_handlers
from handlers.tutorials import register_tutorials_handlers
from handlers.support import register_support_handlers
from handlers.admin import register_admin_handlers
from handlers.menu import register_menu_handlers

logger = get_logger("Main")

def run_flask_webhook():
    """Runs the Flask webhook server on a background thread."""
    logger.info(f"Starting Bohudur webhook listener on http://{WEBHOOK_HOST}:{WEBHOOK_PORT}")
    flask_app.run(host=WEBHOOK_HOST, port=WEBHOOK_PORT, debug=False, use_reloader=False)

def main():
    logger.info("==================================================")
    logger.info("  🚀 Starting Zenix Telegram Digital Shop Bot  ")
    logger.info("==================================================")

    # 1. Initialize SQLite Database
    init_database()

    # 2. Check BOT_TOKEN
    if not BOT_TOKEN or "exampleBotToken" in BOT_TOKEN:
        logger.warning("⚠️ BOT_TOKEN is empty or using placeholder in .env!")
        logger.warning("Please edit .env and set your valid Telegram Bot Token from @BotFather.")
        logger.info("Database and Webhook server are initialized and ready.")
        run_flask_webhook()
        return

    # 3. Create TeleBot instance
    bot = TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=True)
    notification_service.set_bot(bot)

    # 4. Register all handlers in priority order
    logger.info("Registering bot command and callback handlers...")
    register_start_handlers(bot)
    register_shop_handlers(bot)
    register_product_handlers(bot)
    register_orders_handlers(bot)
    register_profile_handlers(bot)
    register_wallet_handlers(bot)
    register_payments_handlers(bot)
    register_referral_handlers(bot)
    register_spin_handlers(bot)
    register_tutorials_handlers(bot)
    register_support_handlers(bot)
    register_admin_handlers(bot)
    register_menu_handlers(bot)

    # 5. Start Webhook Server in Daemon Thread
    webhook_thread = threading.Thread(target=run_flask_webhook, daemon=True)
    webhook_thread.start()

    # 6. Start Polling with auto-reconnect
    logger.info("Bot is active and listening for Telegram updates...")
    while True:
        try:
            bot.infinity_polling(timeout=25, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            logger.error(f"Telegram polling error occurred: {e}", exc_info=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
