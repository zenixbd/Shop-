"""
Payment Service.
Orchestrates payment initialization and official verification.
"""
import uuid
import json
from database import db_transaction, get_connection, get_setting
from services.bohudur_service import bohudur_client
from services.wallet_service import WalletService

class PaymentService:
    @staticmethod
    def create_deposit_payment(user_id: int, amount: float, payment_method="bKash", customer_name="Customer"):
        payment_id = f"PAY-{uuid.uuid4().hex[:10].upper()}"
        success, res, msg = bohudur_client.create_payment(payment_id, user_id, amount, payment_method, customer_name)
        
        with db_transaction() as cur:
            cur.execute("""
            INSERT INTO payments (payment_id, user_id, amount, payment_method, gateway_payment_id, gateway_url, status, raw_response)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?);
            """, (payment_id, user_id, amount, payment_method, (res or {}).get("gateway_payment_id", ""), (res or {}).get("payment_url", ""), json.dumps(res or {})))

        return True, {
            "payment_id": payment_id,
            "amount": amount,
            "payment_method": payment_method,
            "payment_url": (res or {}).get("payment_url")
        }, "Payment created"

    @staticmethod
    def process_and_verify_payment(payment_id: str, submitted_trx_id=None):
        with get_connection() as conn:
            payment = conn.execute("SELECT * FROM payments WHERE payment_id = ?;", (payment_id,)).fetchone()
            if not payment:
                return False, None, "Payment not found"
            if payment["status"] == "SUCCESS":
                return True, dict(payment), "Already verified"

        verified, ver_data, ver_msg = bohudur_client.verify_payment(payment_id, submitted_trx_id)
        if not verified:
            return False, None, ver_msg

        actual_amt = float(ver_data.get("amount", payment["amount"]))
        actual_trx = ver_data.get("trx_id") or submitted_trx_id or f"TRX-{uuid.uuid4().hex[:8].upper()}"

        if actual_amt < float(payment["amount"]):
            return False, None, f"Amount mismatch! Expected ৳{payment['amount']}, received ৳{actual_amt}"

        with db_transaction() as cur:
            cur.execute("SELECT trx_id FROM transactions WHERE trx_id = ?;", (actual_trx,))
            if cur.fetchone():
                return False, None, "Duplicate Transaction ID detected!"

            cur.execute("UPDATE payments SET status = 'SUCCESS', trx_id = ?, verified_at = CURRENT_TIMESTAMP WHERE payment_id = ?;", (actual_trx, payment_id))
            cur.execute("INSERT INTO transactions (trx_id, user_id, amount, trx_type, reference) VALUES (?, ?, ?, 'DEPOSIT', ?);", (actual_trx, payment["user_id"], actual_amt, payment_id))

        WalletService.deposit(payment["user_id"], actual_amt, f"Deposit via {payment['payment_method']}", actual_trx)
        return True, {"payment_id": payment_id, "user_id": payment["user_id"], "amount": actual_amt, "trx_id": actual_trx, "new_balance": WalletService.get_balance(payment["user_id"])}, "Verified"
