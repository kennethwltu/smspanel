"""API SMS endpoints."""

from flask import Blueprint, request

from smspanel import db
from smspanel.models import User, Message, Recipient
from smspanel.services.queue import get_task_queue
from smspanel.utils.sms_helper import process_single_sms_task, process_bulk_sms_task
from smspanel.utils.validation import validate_recipient_list, format_phone_error
from smspanel.api.responses import (
    APIResponse,
    unauthorized,
    bad_request,
    service_unavailable,
    not_found,
)
from smspanel.api.decorators import validate_json

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
        return unauthorized()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    messages = (
        Message.query.filter_by(user_id=user.id)
        .order_by(Message.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return APIResponse.success(
        data={
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
    )


@api_sms_bp.route("/sms", methods=["POST"])
@validate_json(["recipient", "content"])
def send_sms() -> tuple:
    """Send a single SMS message (asynchronous).

    Request body (JSON):
        recipient: str - Phone number (format: +85212345678)
        content: str - Message content

    Returns:
        JSON response with message details (status will be 'pending').
    """
    user = get_user_from_token()
    if user is None:
        return unauthorized()

    data = request.get_json()
    recipient = data.get("recipient")
    content = data.get("content")

    # Validate phone number format
    valid_recipients, invalid_numbers = validate_recipient_list([recipient])
    
    if invalid_numbers:
        return bad_request(
            f"Invalid phone number format: {', '.join(invalid_numbers)}. "
            "Phone number must be in format: +852 followed by 8 digits (e.g., +85212345678).",
            "INVALID_PHONE_FORMAT"
        )

    # Extract the 8-digit part (without +852 prefix) for storage
    phone_digits = valid_recipients[0]

    # Create message record
    message = Message(user_id=user.id, content=content, status="pending")
    db.session.add(message)
    db.session.flush()

    # Create recipient record with 8-digit format
    recipient_record = Recipient(message_id=message.id, phone=phone_digits, status="pending")
    db.session.add(recipient_record)
    db.session.commit()

    # Enqueue background task with 8-digit format
    task_queue = get_task_queue()
    enqueued = task_queue.enqueue(process_single_sms_task, message.id, phone_digits)

    if not enqueued:
        return service_unavailable()

    return APIResponse.success(
        data={
            "id": message.id,
            "status": "pending",
            "recipient": recipient,  # Return original format with +852
            "content": content,
            "created_at": message.created_at.isoformat(),
        },
        message="SMS queued for sending",
        status_code=202,
    )


@api_sms_bp.route("/sms/send-bulk", methods=["POST"])
@validate_json(["recipients", "content"])
def send_bulk_sms() -> tuple:
    """Send SMS messages to multiple recipients (asynchronous).

    Request body (JSON):
        recipients: list[str] - List of phone numbers (format: +85212345678)
        content: str - Message content

    Returns:
        JSON response with message details (status will be 'pending').
    """
    user = get_user_from_token()
    if user is None:
        return unauthorized()

    data = request.get_json()
    recipients = data.get("recipients", [])
    content = data.get("content")

    # Additional validation for non-empty recipients list
    if not recipients:
        return bad_request("Recipients list cannot be empty", "MISSING_FIELDS")

    # Validate phone number format
    valid_recipients, invalid_numbers = validate_recipient_list(recipients)
    
    if invalid_numbers:
        return bad_request(
            f"Invalid phone number format: {', '.join(invalid_numbers)}. "
            "Phone numbers must be in format: +852 followed by 8 digits (e.g., +85212345678).",
            "INVALID_PHONE_FORMAT"
        )

    # Create message record
    message = Message(user_id=user.id, content=content, status="pending")
    db.session.add(message)
    db.session.flush()

    # Create recipient records with 8-digit format
    for phone_digits in valid_recipients:
        recipient_record = Recipient(message_id=message.id, phone=phone_digits, status="pending")
        db.session.add(recipient_record)

    db.session.commit()

    # Enqueue background task with 8-digit format
    task_queue = get_task_queue()
    enqueued = task_queue.enqueue(process_bulk_sms_task, message.id, valid_recipients)

    if not enqueued:
        return service_unavailable()

    return APIResponse.success(
        data={
            "id": message.id,
            "status": "pending",
            "total": len(recipients),  # Return original count
            "content": content,
            "created_at": message.created_at.isoformat(),
        },
        message="Bulk SMS queued for sending",
        status_code=202,
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
        return unauthorized()

    message = Message.query.filter_by(id=message_id, user_id=user.id).first()
    if message is None:
        return not_found("Message not found")

    return APIResponse.success(
        data={
            "id": message.id,
            "content": message.content,
            "status": message.status,
            "created_at": message.created_at.isoformat(),
            "sent_at": message.sent_at.isoformat() if message.sent_at else None,
            "hkt_response": message.hkt_response,
            "recipient_count": message.recipient_count,
            "success_count": message.success_count,
            "failed_count": message.failed_count,
            "job_status": message.job_status,
            "queue_position": message.queue_position,
            "estimated_complete_at": (
                message.estimated_complete_at.isoformat() if message.estimated_complete_at else None
            ),
        }
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
        return unauthorized()

    message = Message.query.filter_by(id=message_id, user_id=user.id).first()
    if message is None:
        return not_found("Message not found")

    recipients = [
        {
            "id": r.id,
            "phone": r.phone,
            "status": r.status,
            "error_message": r.error_message,
        }
        for r in message.recipients
    ]

    return APIResponse.success(data={"recipients": recipients})
