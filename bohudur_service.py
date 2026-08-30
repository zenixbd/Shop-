"""
Bohudur Payment Gateway Service.
Handles payment invoice creation, official status query/verification,
and secure webhook signature validation for bKash, Nagad, and Rocket.
"""

import hmac
import hashlib
import json
import requests
from typing import Dict, Any, Optional, Tuple
from config import (
    BOHUDUR_API_BASE_URL,
    BOHUDUR_API_KEY,
    BOHUDUR_API_SECRET,
    BOHUDUR_MERCHANT_ID,
    BOHUDUR_WEBHOOK_SECRET,
    WEBHOOK_URL
)
from utils.logger import get_logger

logger = get_logger("BohudurService")

class BohudurService:
    def __init__(self):
        self.base_url = BOHUDUR_API_BASE_URL
        self.api_key = BOHUDUR_API_KEY
        self.api_secret = BOHUDUR_API_SECRET
        self.merchant_id = BOHUDUR_MERCHANT_ID
        self.webhook_secret = BOHUDUR_WEBHOOK_SECRET
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": self.api_key,
            "X-API-SECRET": self.api_secret,
            "X-MERCHANT-ID": self.merchant_id,
            "User-Agent": "ZenixShopBot-BohudurClient/1.0"
        })

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def create_payment(
        self,
        payment_id: str,
        user_id: int,
        amount: float,
        payment_method: str = "bKash",
        customer_name: str = "Customer",
        customer_phone: str = "01700000000"
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        if not self.is_configured():
            return False, None, "Bohudur API credentials are not configured in .env"

        url = f"{self.base_url}/checkout/create"
        callback_endpoint = WEBHOOK_URL if WEBHOOK_URL else "https://your-domain.com/payment/webhook/bohudur"
        
        payload = {
            "merchant_id": self.merchant_id,
            "invoice_id": payment_id,
            "amount": float(amount),
            "currency": "BDT",
            "payment_method": payment_method.lower(),
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_id": str(user_id),
            "redirect_url": callback_endpoint,
            "callback_url": callback_endpoint,
            "metadata": {
                "user_id": user_id,
                "bot_payment_id": payment_id,
                "platform": "telegram_bot"
            }
        }

        try:
            logger.info(f"Initiating Bohudur payment for Payment ID: {payment_id}, User: {user_id}, Amount: ৳{amount}")
            response = self.session.post(url, json=payload, timeout=20)
            
            if response.status_code in (200, 201):
                data = response.json()
                if data.get("status") in ("success", True, "SUCCESS") or "payment_url" in data:
                    payment_url = data.get("payment_url") or data.get("checkout_url") or data.get("data", {}).get("payment_url")
                    gateway_id = data.get("gateway_payment_id") or data.get("transaction_id") or data.get("data", {}).get("id")
                    
                    return True, {
                        "payment_url": payment_url,
                        "gateway_payment_id": gateway_id,
                        "raw": data
                    }, "Payment invoice created successfully"
                else:
                    err_msg = data.get("message") or "Gateway returned unsuccessful status"
                    return False, data, err_msg
            else:
                return False, None, f"Payment gateway error (HTTP {response.status_code})"

        except Exception as e:
            logger.error(f"Error in Bohudur create_payment: {e}")
            return False, None, f"Communication error: {str(e)}"

    def verify_payment(self, payment_id: str, trx_id: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        if not self.is_configured():
            return False, None, "Bohudur API credentials are not configured"

        url = f"{self.base_url}/checkout/verify"
        payload = {
            "merchant_id": self.merchant_id,
            "invoice_id": payment_id
        }
        if trx_id:
            payload["transaction_id"] = trx_id

        try:
            response = self.session.post(url, json=payload, timeout=20)
            if response.status_code == 200:
                data = response.json()
                status = str(data.get("status") or data.get("payment_status") or data.get("data", {}).get("status")).upper()
                verified_amount = float(data.get("amount") or data.get("data", {}).get("amount", 0.0))
                verified_trx = data.get("transaction_id") or data.get("bank_trx_id") or data.get("data", {}).get("transaction_id")
                
                if status in ("SUCCESS", "COMPLETED", "PAID"):
                    return True, {
                        "status": "SUCCESS",
                        "amount": verified_amount,
                        "trx_id": verified_trx,
                        "raw": data
                    }, "Payment verified by official gateway"
                else:
                    return False, data, f"Payment status is {status}"
            else:
                return False, None, f"Verification failed with status {response.status_code}"
        except Exception as e:
            return False, None, f"Verification error: {str(e)}"

    def validate_webhook_signature(self, payload_body: bytes, received_signature: str) -> bool:
        secret = self.webhook_secret or self.api_secret
        if not secret or not received_signature:
            return False
        computed = hmac.new(secret.encode("utf-8"), payload_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, received_signature)

bohudur_client = BohudurService()
