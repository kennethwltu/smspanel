"""API SMS endpoints."""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify

from .. import db
from ..models import User, Message, Recipient
from ..services.hkt_sms import HKTSMSService

api_sms_bp = Blueprint("api_sms", __name__)


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
                    "success_count": m.success_count,
                    "failed_count": m.failed_count,
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
    """Send a single SMS message.

    Request body (JSON):
        recipient: str - Phone number
        content: str - Message content

    Returns:
        JSON response with message details.
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

    # Send SMS via HKT
    sms_service = HKTSMSService()
    result = sms_service.send_single(recipient, content)

    # Update records based on result
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

    return (
        jsonify(
            {
                "id": message.id,
                "status": message.status,
                "recipient": recipient,
                "content": content,
                "created_at": message.created_at.isoformat(),
            }
        ),
        200 if result["success"] else 500,
    )


@api_sms_bp.route("/sms/send-bulk", methods=["POST"])
def send_bulk_sms() -> tuple:
    """Send SMS messages to multiple recipients.

    Request body (JSON):
        recipients: list[str] - List of phone numbers
        content: str - Message content

    Returns:
        JSON response with message details.
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

    # Send SMS via HKT
    sms_service = HKTSMSService()
    result = sms_service.send_bulk(recipients, content)

    # Update records based on result
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

    return (
        jsonify(
            {
                "id": message.id,
                "status": message.status,
                "total": result["total"],
                "successful": result["successful"],
                "failed": result["failed"],
                "content": content,
                "created_at": message.created_at.isoformat(),
            }
        ),
        200 if all_sent else 207 if result["successful"] > 0 else 500,
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
