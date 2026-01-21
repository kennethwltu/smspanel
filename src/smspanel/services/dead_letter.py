"""Dead letter queue service for persisting failed SMS messages."""

import logging
from typing import Optional, List

from ..models import db, DeadLetterMessage

logger = logging.getLogger(__name__)


class DeadLetterQueue:
    """Service for managing dead letter queue of failed SMS messages."""

    def __init__(self, max_retries: int = 3):
        """Initialize dead letter queue service.

        Args:
            max_retries: Maximum number of retry attempts before abandoning.
        """
        self.max_retries = max_retries

    def add(
        self,
        message_id: Optional[int],
        recipient: str,
        content: str,
        error_message: str,
        error_type: str,
    ) -> DeadLetterMessage:
        """Add a failed message to the dead letter queue.

        Args:
            message_id: ID of the original message (if any).
            recipient: Phone number of recipient.
            content: SMS message content.
            error_message: Description of the error.
            error_type: Type of error (e.g., "ConnectionError").

        Returns:
            The created DeadLetterMessage instance.
        """
        dead_letter = DeadLetterMessage(
            message_id=message_id,
            recipient=recipient,
            content=content,
            error_message=error_message,
            error_type=error_type,
            retry_count=0,
            max_retries=self.max_retries,
            status="pending",
        )

        db.session.add(dead_letter)
        db.session.commit()

        logger.info(f"Added failed SMS to dead letter queue: {dead_letter}")
        return dead_letter

    def get_pending(self, limit: int = 100) -> List[DeadLetterMessage]:
        """Get all pending messages ready for retry.

        Args:
            limit: Maximum number of messages to return.

        Returns:
            List of pending DeadLetterMessage instances.
        """
        return (
            DeadLetterMessage.query.filter_by(status="pending")
            .filter(DeadLetterMessage.retry_count < DeadLetterMessage.max_retries)
            .order_by(DeadLetterMessage.created_at.asc())
            .limit(limit)
            .all()
        )

    def get_all(self, status: Optional[str] = None, limit: int = 100) -> List[DeadLetterMessage]:
        """Get all dead letter messages, optionally filtered by status.

        Args:
            status: Optional status filter ("pending", "retried", "abandoned").
            limit: Maximum number of messages to return.

        Returns:
            List of DeadLetterMessage instances.
        """
        query = DeadLetterMessage.query

        if status:
            query = query.filter_by(status=status)

        return query.order_by(DeadLetterMessage.created_at.desc()).limit(limit).all()

    def retry(self, dead_letter_id: int) -> bool:
        """Mark a dead letter message for retry.

        Args:
            dead_letter_id: ID of the dead letter message.

        Returns:
            True if marked for retry, False if max retries exceeded.
        """
        dead_letter = DeadLetterMessage.query.get(dead_letter_id)
        if not dead_letter:
            logger.warning(f"Dead letter message {dead_letter_id} not found")
            return False

        if not dead_letter.can_retry():
            logger.warning(
                f"Dead letter {dead_letter_id} cannot be retried (retry_count={dead_letter.retry_count})"
            )
            return False

        dead_letter.increment_retry()
        db.session.commit()

        logger.info(
            f"Dead letter {dead_letter_id} marked for retry (attempt {dead_letter.retry_count})"
        )
        return True

    def mark_retried(self, dead_letter_id: int) -> bool:
        """Mark a dead letter message as successfully retried.

        Args:
            dead_letter_id: ID of the dead letter message.

        Returns:
            True if marked successfully, False if not found.
        """
        dead_letter = DeadLetterMessage.query.get(dead_letter_id)
        if not dead_letter:
            return False

        dead_letter.mark_retried()
        db.session.commit()

        logger.info(f"Dead letter {dead_letter_id} marked as retried")
        return True

    def mark_abandoned(self, dead_letter_id: int) -> bool:
        """Mark a dead letter message as abandoned.

        Args:
            dead_letter_id: ID of the dead letter message.

        Returns:
            True if marked successfully, False if not found.
        """
        dead_letter = DeadLetterMessage.query.get(dead_letter_id)
        if not dead_letter:
            return False

        dead_letter.mark_abandoned()
        db.session.commit()

        logger.info(f"Dead letter {dead_letter_id} marked as abandoned")
        return True

    def get_stats(self) -> dict:
        """Get statistics about the dead letter queue.

        Returns:
            Dict with counts by status.
        """
        pending = DeadLetterMessage.query.filter_by(status="pending").count()
        retried = DeadLetterMessage.query.filter_by(status="retried").count()
        abandoned = DeadLetterMessage.query.filter_by(status="abandoned").count()

        return {
            "pending": pending,
            "retried": retried,
            "abandoned": abandoned,
            "total": pending + retried + abandoned,
        }


# Global dead letter queue instance
_dead_letter_queue: Optional[DeadLetterQueue] = None


def get_dead_letter_queue() -> DeadLetterQueue:
    """Get the global dead letter queue instance.

    Returns:
        The global DeadLetterQueue instance.
    """
    global _dead_letter_queue
    if _dead_letter_queue is None:
        _dead_letter_queue = DeadLetterQueue()
    return _dead_letter_queue


def init_dead_letter_queue(app, max_retries: int = 3):
    """Initialize the dead letter queue with Flask app.

    Args:
        app: Flask application instance.
        max_retries: Maximum retry attempts before abandoning.
    """
    global _dead_letter_queue
    _dead_letter_queue = DeadLetterQueue(max_retries=max_retries)

    # Create tables
    with app.app_context():
        db.create_all()
