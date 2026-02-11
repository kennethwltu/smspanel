"""Helper utilities for SMS operations."""

import logging
from datetime import datetime, timezone
from typing import Any

from smspanel import db
from smspanel.models import Message, Recipient
from smspanel.services.hkt_sms import HKTSMSService

logger = logging.getLogger(__name__)


# Global SMS service instance (will be initialized with config)
_sms_service: HKTSMSService | None = None


def init_sms_service(config_service):
    """Initialize SMS service with config dependency.

    Args:
        config_service: Configuration service instance.
    """
    global _sms_service
    _sms_service = HKTSMSService(config_service)


def get_sms_service() -> HKTSMSService:
    """Get the SMS service instance.

    Returns:
        HKTSMSService instance.

    Raises:
        RuntimeError: If SMS service not initialized.
    """
    if _sms_service is None:
        raise RuntimeError("SMS service not initialized. Call init_sms_service() first.")
    return _sms_service


def create_message_record(user_id: int, content: str) -> Message:
    """Create a new message record.

    Args:
        user_id: User ID.
        content: Message content.

    Returns:
        The created Message record.
    """
    message = Message(user_id=user_id, content=content, status="pending")
    db.session.add(message)
    db.session.flush()
    return message


def create_recipient_records(message_id: int, phone_numbers: list[str]) -> None:
    """Create recipient records for a message.

    Args:
        message_id: Message ID.
        phone_numbers: List of phone numbers.
    """
    for phone in phone_numbers:
        recipient_record = Recipient(message_id=message_id, phone=phone, status="pending")
        db.session.add(recipient_record)


def update_message_status_from_result(message: Message, result: dict[str, Any]) -> None:
    """Update message status based on SMS send result.

    Args:
        message: Message to update.
        result: Result dict from HKT SMS service.
    """
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


def update_single_sms_status(
    message: Message, recipient: Recipient, result: dict[str, Any]
) -> None:
    """Update status for single SMS send.

    Args:
        message: Message to update.
        recipient: Recipient record to update.
        result: Result dict from HKT SMS service.
    """
    if result["success"]:
        message.status = "sent"
        message.sent_at = datetime.now(timezone.utc)
        message.hkt_response = result.get("response_text", "")
        recipient.status = "sent"
    else:
        message.status = "failed"
        recipient.status = "failed"
        recipient.error_message = result.get("error", "Unknown error")


def get_flash_message_from_result(result: dict[str, Any]) -> tuple[str, str]:
    """Get flash message type and content based on SMS result.

    Args:
        result: Result dict from HKT SMS service.

    Returns:
        Tuple of (message_type, message_content).
        message_type: "success", "warning", or "error".
    """
    all_sent = result["success"]
    if all_sent:
        return "success", f"Successfully sent {result['total']} message(s)."
    elif result["successful"] > 0:
        return (
            "warning",
            f"Partially sent: {result['successful']} successful, {result['failed']} failed.",
        )
    else:
        return "error", "Failed to send messages. Please try again."


def process_single_sms_task(message_id: int, recipient: str) -> None:
    """Background task to send a single SMS.

    Args:
        message_id: Message ID in database.
        recipient: Phone number to send to (8-digit format).
    """
    message = Message.query.get(message_id)
    if not message:
        logger.error(f"Message {message_id} not found")
        return

    recipient_record = Recipient.query.filter_by(message_id=message_id, phone=recipient).first()
    if not recipient_record:
        logger.error(f"Recipient record not found for message {message_id}, phone {recipient}")
        return

    sms_service = get_sms_service()
    # Convert 8-digit format to "85212345678" format for SMS service
    formatted_recipient = f"852{recipient}"
    result = sms_service.send_single(formatted_recipient, message.content)

    update_single_sms_status(message, recipient_record, result)
    db.session.commit()


def process_bulk_sms_task(message_id: int, recipients: list[str]) -> None:
    """Background task to send bulk SMS.

    Args:
        message_id: Message ID in database.
        recipients: List of phone numbers to send to (8-digit format).
    """
    message = Message.query.get(message_id)
    if not message:
        logger.error(f"Message {message_id} not found")
        return

    sms_service = get_sms_service()
    # Convert 8-digit format to "85212345678" format for SMS service
    formatted_recipients = [f"852{recipient}" for recipient in recipients]
    result = sms_service.send_bulk(formatted_recipients, message.content)

    update_message_status_from_result(message, result)
    db.session.commit()
