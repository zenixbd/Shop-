"""
Webhook Server.
Exposes HTTPS webhooks for Bohudur Payment Gateway (bKash/Nagad).
"""
from flask import Flask, request, jsonify
from services.payment_service import PaymentService
from services.bohudur_service import bohudur_client
from services.notification_service import notification_service
from utils.logger import get_logger

logger = get_logger("WebhookServer")
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "Telegram Shop Bot"}), 200

@app.route("/payment/webhook/bohudur", methods=["POST"])
def bohudur_payment_webhook():
    signature = request.headers.get("X-BOHUDUR-SIGNATURE")
    raw_body = request.get_data()

    if signature and bohudur_client.webhook_secret:
        if not bohudur_client.validate_webhook_signature(raw_body, signature):
            return jsonify({"status": "error", "message": "Invalid HMAC signature"}), 401

    payload = request.get_json(force=True)
    payment_id = payload.get("invoice_id") or payload.get("payment_id")
    trx_id = payload.get("transaction_id")
    status = str(payload.get("status", "")).upper()

    if not payment_id or status not in ("SUCCESS", "COMPLETED", "PAID"):
        return jsonify({"status": "acknowledged"}), 200

    success, data, msg = PaymentService.process_and_verify_payment(payment_id, submitted_trx_id=trx_id)
    if success:
        notification_service.notify_user_payment_success(data["user_id"], data["amount"], data.get("trx_id", trx_id), data["new_balance"])
        return jsonify({"status": "success", "invoice_id": payment_id}), 200
    return jsonify({"status": "failed", "reason": msg}), 400
