"""
Wallet Service.
Provides thread-safe atomic wallet operations.
"""
from typing import Optional, Dict, Any, List, Tuple
from database import db_transaction, get_connection
from utils.logger import get_logger
from config import CURRENCY_SYMBOL

logger = get_logger("WalletService")

class WalletService:
    @staticmethod
    def get_or_create_user(user_id: int, username=None, first_name=None, last_name=None, referred_by=None):
        with db_transaction() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,))
            user = cur.fetchone()
            if not user:
                valid_referrer = referred_by if (referred_by and referred_by != user_id) else None
                cur.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, balance, referred_by)
                VALUES (?, ?, ?, ?, 0.0, ?);
                """, (user_id, username or "", first_name or "", last_name or "", valid_referrer))
                if valid_referrer:
                    cur.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_user_id) VALUES (?, ?);", (valid_referrer, user_id))
                cur.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,))
                user = cur.fetchone()
            return dict(user)

    @staticmethod
    def get_balance(user_id: int) -> float:
        with get_connection() as conn:
            row = conn.execute("SELECT balance FROM users WHERE user_id = ?;", (user_id,)).fetchone()
            return float(row["balance"]) if row else 0.0

    @staticmethod
    def deposit(user_id: int, amount: float, description="Deposit", reference_id=None):
        with db_transaction() as cur:
            cur.execute("SELECT balance FROM users WHERE user_id = ?;", (user_id,))
            row = cur.fetchone()
            if not row:
                return False, 0.0, "User not found"
            curr = float(row["balance"])
            new_bal = round(curr + amount, 2)
            cur.execute("UPDATE users SET balance = ?, total_deposits = total_deposits + ? WHERE user_id = ?;", (new_bal, amount, user_id))
            cur.execute("INSERT INTO wallet_transactions (user_id, type, amount, balance_before, balance_after, description, reference_id) VALUES (?, 'DEPOSIT', ?, ?, ?, ?, ?);", (user_id, amount, curr, new_bal, description, reference_id or ""))
            return True, new_bal, "Balance deposited"

    @staticmethod
    def deduct_for_purchase(user_id: int, amount: float, order_id: str, product_name: str):
        with db_transaction() as cur:
            cur.execute("SELECT balance FROM users WHERE user_id = ?;", (user_id,))
            row = cur.fetchone()
            if not row:
                return False, 0.0, "User not found"
            curr = float(row["balance"])
            if curr < amount:
                return False, curr, f"Insufficient balance. Need {CURRENCY_SYMBOL}{amount:.2f}, you have {CURRENCY_SYMBOL}{curr:.2f}"
            new_bal = round(curr - amount, 2)
            cur.execute("UPDATE users SET balance = ?, total_orders = total_orders + 1 WHERE user_id = ?;", (new_bal, user_id))
            cur.execute("INSERT INTO wallet_transactions (user_id, type, amount, balance_before, balance_after, description, reference_id) VALUES (?, 'PURCHASE', ?, ?, ?, ?, ?);", (user_id, amount, curr, new_bal, f"Purchase: {product_name}", order_id))
            return True, new_bal, "Payment deducted"
