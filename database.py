"""
Database module for Telegram Digital Product Shop Bot.
Handles SQLite schema creation, migrations, connection management,
atomic transaction context managers, and default system settings initialization.
"""

import sqlite3
import os
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any, List
from config import DATABASE_PATH, ADMIN_ID
from utils.logger import get_logger

logger = get_logger("Database")

db_file_path = Path(DATABASE_PATH)
db_file_path.parent.mkdir(parents=True, exist_ok=True)

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

@contextmanager
def db_transaction() -> Generator[sqlite3.Cursor, None, None]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE TRANSACTION;")
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def init_database() -> None:
    logger.info("Initializing SQLite database tables...")
    with db_transaction() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance REAL DEFAULT 0.0,
            total_orders INTEGER DEFAULT 0,
            total_deposits REAL DEFAULT 0.0,
            referral_earnings REAL DEFAULT 0.0,
            referred_by INTEGER,
            is_banned INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT NOT NULL DEFAULT 'MANAGER',
            added_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL DEFAULT 'General',
            platform TEXT DEFAULT 'All',
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            delivery_type TEXT NOT NULL DEFAULT 'TEXT',
            delivery_content TEXT,
            image TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS product_stock (
            stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            item_content TEXT NOT NULL,
            is_used INTEGER DEFAULT 0,
            used_by_order_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            used_at DATETIME,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            amount REAL NOT NULL,
            delivery_type TEXT NOT NULL,
            delivery_content TEXT,
            status TEXT NOT NULL DEFAULT 'COMPLETED',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            trx_id TEXT,
            gateway_payment_id TEXT,
            gateway_url TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            raw_response TEXT,
            verified_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            trx_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            trx_type TEXT NOT NULL,
            reference TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            balance_before REAL NOT NULL,
            balance_after REAL NOT NULL,
            description TEXT,
            reference_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            referrer_id INTEGER NOT NULL,
            referred_user_id INTEGER NOT NULL PRIMARY KEY,
            status TEXT DEFAULT 'ACTIVE',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS referral_earnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_user_id INTEGER NOT NULL,
            order_id TEXT,
            amount REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tutorials (
            tutorial_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            media_type TEXT DEFAULT 'TEXT',
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            assigned_to_admin_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS support_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            sender_type TEXT NOT NULL,
            sender_id INTEGER NOT NULL,
            message_text TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS spin_rewards (
            reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reward_name TEXT NOT NULL,
            reward_type TEXT NOT NULL,
            reward_value REAL NOT NULL,
            probability_weight INTEGER NOT NULL DEFAULT 10,
            is_active INTEGER DEFAULT 1
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS spin_history (
            spin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reward_name TEXT NOT NULL,
            reward_type TEXT NOT NULL,
            reward_value REAL NOT NULL,
            is_free INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            broadcast_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            target_group TEXT NOT NULL,
            message_type TEXT NOT NULL,
            content TEXT NOT NULL,
            media_id TEXT,
            total_sent INTEGER DEFAULT 0,
            total_failed INTEGER DEFAULT 0,
            status TEXT DEFAULT 'PENDING',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            target_id TEXT,
            action TEXT NOT NULL,
            reason TEXT,
            details_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
