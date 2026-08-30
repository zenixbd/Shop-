"""
Order Service.
Coordinates atomic product purchase, stock assignment, and fulfillment.
"""
import uuid
from typing import Dict, Any, Optional, List, Tuple
from database import db_transaction, get_connection, get_setting
from services.wallet_service import WalletService
from services.delivery_service import DeliveryService
from services.referral_service import ReferralService

class OrderService:
    @staticmethod
    def create_order(user_id: int, product_id: int) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        with get_connection() as conn:
            product_row = conn.execute("SELECT * FROM products WHERE product_id = ?;", (product_id,)).fetchone()
            if not product_row:
                return False, None, "Product not found."
            product = dict(product_row)
            if product.get("status") != "ACTIVE" or product.get("stock", 0) <= 0:
                return False, None, "Product is currently unavailable or out of stock."

        price = float(product["price"])
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        success, new_balance, msg = WalletService.deduct_for_purchase(user_id, price, order_id, product["name"])
        if not success:
            return False, {"price": price, "current_balance": new_balance}, msg

        delivery_type = product.get("delivery_type", "TEXT")
        if delivery_type in ("LICENSE_KEY", "CODE"):
            assigned_key = DeliveryService.get_and_assign_stock_item(product_id, order_id)
            final_content = assigned_key or product.get("delivery_content") or "Key pending"
        else:
            final_content = product.get("delivery_content") or "Service activated."
            with db_transaction() as cur:
                cur.execute("UPDATE products SET stock = MAX(0, stock - 1) WHERE product_id = ?;", (product_id,))

        with db_transaction() as cur:
            cur.execute("""
            INSERT INTO orders (order_id, user_id, product_id, product_name, amount, delivery_type, delivery_content, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'COMPLETED');
            """, (order_id, user_id, product_id, product["name"], price, delivery_type, final_content))
            cur.execute("INSERT INTO order_items (order_id, item_content) VALUES (?, ?);", (order_id, final_content))

        ReferralService.process_order_referral_reward(user_id, order_id, price)
        formatted = DeliveryService.format_delivery_message(product, final_content)

        return True, {
            "order_id": order_id,
            "user_id": user_id,
            "product_name": product["name"],
            "amount": price,
            "delivery_type": delivery_type,
            "formatted_delivery": formatted,
            "new_balance": new_balance
        }, "Order completed"
