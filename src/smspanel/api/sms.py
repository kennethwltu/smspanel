"""API SMS endpoints."""

import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify

from .. import db
from ..models import User, Message, Recipient
from ..services.hkt_sms import HKTSMSService
from ..services.queue import get_task_queue

logger = logging.getLogger(__name__)

api_sms_bp = Blueprint("api_sms", __name__)


def _process_single_sms(message_id: int, recipient: str):
    """Background task to send a single SMS.

    Args:
        message_id: Message ID in database.
        recipient: Phone number to send to.
    """

    message = Message.query.get(message_id)
    if not message:
        logger.error(f"Message {message_id} not found")
        return

    recipient_record = Recipient.query.filter_by(message_id=message_id, phone=recipient).first()
    if not recipient_record:
        logger.error(f"Recipient record not found for message {message_id}, phone {recipient}")
        return

    sms_service = HKTSMSService()
    result = sms_service.send_single(recipient, message.content)

    if result["success"]:
        message.status = "sent"
        message.sent_at = datetime.now(timezone.utc)
        message.hkt_response = result.get("response_text", "")
        recipient_record.status = "sent"
    else:
        message.status = "failed"
        recipient_record.status = "failed"
        recipient_record.error_message = result.get("error", "Unknown error")

    db.session.commit()


def _process_bulk_sms(message_id: int, recipients: list[str]):
    """Background task to send bulk SMS.

    Args:
        message_id: Message ID in database.
        recipients: List of phone numbers to send to.
    """

    message = Message.query.get(message_id)
    if not message:
        logger.error(f"Message {message_id} not found")
        return

    sms_service = HKTSMSService()
    result = sms_service.send_bulk(recipients, message.content)

    all_sent = result["success"]
    message.status = "sent" if all_sent else "partial" if result["successful"] > 0 else "failed"
    if all_sent:
        message.sent_at = datetime.now(timezone.utc)

    # Update individual recipient statuses
    for i, recipient_result in enumerate(result["results"]):
        recipient_record = message.recipients[i]
        if recipient_result["success"]:
            recipient_record.status = "sent"
        else:
            recipient_record.status = "failed"
            recipient_record.error_message = recipient_result.get("error", "Unknown error")

    db.session.commit()


def get_user_from_token() -> User | None:
    """Get user from API token.

    Returns:
        User object or None if invalid.
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]

    return User.query.filter_by(token=token).first()


@api_sms_bp.route("/sms", methods=["GET"])
def list_messages() -> tuple:
    """List all messages for the authenticated user.

    Query parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20)

    Returns:
        JSON response with messages list.
    """
    user = get_user_from_token()
    if user is None:
        return jsonify({"error": "Unauthorized"}), 401

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    messages = (
        Message.query.filter_by(user_id=user.id)
        .order_by(Message.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify(
        {
            "messages": [
                {
                    "id": m.id,
                    "content": m.content,
                    "status": m.status,
                    "created_at": m.created_at.isoformat(),
                    "recipient_count": m.recipient_count,
                    "recipients": [r.phone for r in m.recipients],
                }
                for m in messages.items
            ],
            "total": messages.total,
            "pages": messages.pages,
            "current_page": page,
        }
    ), 200


@api_sms_bp.route("/sms", methods=["POST"])
def send_sms() -> tuple:
    """Send a single SMS message (asynchronous).

    Request body (JSON):
        recipient: str - Phone number
        content: str - Message content

    Returns:
        JSON response with message details (status will be 'pending').
    """
    user = get_user_from_token()
    if user is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    recipient = data.get("recipient")
    content = data.get("content")

    if not recipient or not content:
        return jsonify({"error": "Recipient and content are required"}), 400

    # Create message record
    message = Message(user_id=user.id, content=content, status="pending")
    db.session.add(message)
    db.session.flush()

    # Create recipient record
    recipient_record = Recipient(message_id=message.id, phone=recipient, status="pending")
    db.session.add(recipient_record)
    db.session.commit()

    # Enqueue background task
    task_queue = get_task_queue()
    enqueued = task_queue.enqueue(_process_single_sms, message.id, recipient)

    if not enqueued:
        return jsonify({"error": "Service is busy, please try again later"}), 503

    return (
        jsonify(
            {
                "id": message.id,
                "status": "pending",
                "recipient": recipient,
                "content": content,
                "created_at": message.created_at.isoformat(),
                "message": "SMS queued for sending",
            }
        ),
        202,
    )


@api_sms_bp.route("/sms/send-bulk", methods=["POST"])
def send_bulk_sms() -> tuple:
    """Send SMS messages to multiple recipients (asynchronous).

    Request body (JSON):
        recipients: list[str] - List of phone numbers
        content: str - Message content

    Returns:
        JSON response with message details (status will be 'pending').
    """
    user = get_user_from_token()
    if user is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    recipients = data.get("recipients", [])
    content = data.get("content")

    if not recipients or not content:
        return jsonify({"error": "Recipients and content are required"}), 400

    # Create message record
    message = Message(user_id=user.id, content=content, status="pending")
    db.session.add(message)
    db.session.flush()

    # Create recipient records
    for recipient in recipients:
        recipient_record = Recipient(message_id=message.id, phone=recipient, status="pending")
        db.session.add(recipient_record)

    db.session.commit()

    # Enqueue background task
    task_queue = get_task_queue()
    enqueued = task_queue.enqueue(_process_bulk_sms, message.id, recipients)

    if not enqueued:
        return jsonify({"error": "Service is busy, please try again later"}), 503

    return (
        jsonify(
            {
                "id": message.id,
                "status": "pending",
                "total": len(recipients),
                "content": content,
                "created_at": message.created_at.isoformat(),
                "message": "Bulk SMS queued for sending",
            }
        ),
        202,
    )


@api_sms_bp.route("/sms/<int:message_id>", methods=["GET"])
def get_message(message_id: int) -> tuple:
    """Get details of a specific message.

    Args:
        message_id: Message ID

    Returns:
        JSON response with message details.
    """
    user = get_user_from_token()
    if user is None:
        return jsonify({"error": "Unauthorized"}), 401

    message = Message.query.filter_by(id=message_id, user_id=user.id).first_or_404()

    return (
        jsonify(
            {
                "id": message.id,
                "content": message.content,
                "status": message.status,
                "created_at": message.created_at.isoformat(),
                "sent_at": message.sent_at.isoformat() if message.sent_at else None,
                "hkt_response": message.hkt_response,
                "recipient_count": message.recipient_count,
                "success_count": message.success_count,
                "failed_count": message.failed_count,
            }
        ),
        200,
    )


@api_sms_bp.route("/sms/<int:message_id>/recipients", methods=["GET"])
def get_message_recipients(message_id: int) -> tuple:
    """Get recipient details for a specific message.

    Args:
        message_id: Message ID

    Returns:
        JSON response with recipient details.
    """
    user = get_user_from_token()
    if user is None:
        return jsonify({"error": "Unauthorized"}), 401

    message = Message.query.filter_by(id=message_id, user_id=user.id).first_or_404()

    recipients = [
        {
            "id": r.id,
            "phone": r.phone,
            "status": r.status,
            "error_message": r.error_message,
        }
        for r in message.recipients
    ]

    return jsonify({"recipients": recipients}), 200
