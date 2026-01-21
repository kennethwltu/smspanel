"""Database models for the SMS application."""

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import secrets

from .extensions import db


class User(UserMixin, db.Model):
    """User model for authentication."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    messages = db.relationship(
        "Message", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def generate_token() -> str:
        """Generate a random API token.

        Returns:
            Random 64-character URL-safe token.
        """
        return secrets.token_urlsafe(48)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Message(db.Model):
    """Message model for SMS messages."""

    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending", index=True)  # pending, sent, failed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    hkt_response = db.Column(db.Text, nullable=True)

    recipients = db.relationship(
        "Recipient", backref="message", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def recipient_count(self) -> int:
        """Get the total number of recipients."""
        return self.recipients.count()

    @property
    def success_count(self) -> int:
        """Get the number of successfully sent SMS."""
        return self.recipients.filter_by(status="sent").count()

    @property
    def failed_count(self) -> int:
        """Get the number of failed SMS."""
        return self.recipients.filter_by(status="failed").count()

    def __repr__(self) -> str:
        return f"<Message {self.id}: {self.content[:30]}...>"


class Recipient(db.Model):
    """Recipient model for tracking individual SMS delivery status."""

    __tablename__ = "recipients"

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("messages.id"), nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, sent, failed
    error_message = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Recipient {self.phone}: {self.status}>"


class DeadLetterMessage(db.Model):
    """Model for persisting failed SMS messages for later reprocessing.

    This serves as a dead letter queue where SMS messages that fail
    after all retry attempts are stored for manual review and retry.
    """

    __tablename__ = "dead_letter_messages"

    id = db.Column(db.Integer, primary_key=True)
    # Reference to original message
    message_id = db.Column(db.Integer, db.ForeignKey("messages.id"), nullable=True, index=True)
    # Recipient information
    recipient = db.Column(db.String(20), nullable=False, index=True)
    # Message content
    content = db.Column(db.Text, nullable=False)
    # Error details
    error_message = db.Column(db.Text, nullable=True)
    error_type = db.Column(db.String(50), nullable=True)  # e.g., "ConnectionError", "Timeout"
    # Retry tracking
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    # Status
    status = db.Column(db.String(20), default="pending", index=True)  # pending, retried, abandoned
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    retried_at = db.Column(db.DateTime, nullable=True)
    last_attempt_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<DeadLetterMessage {self.id}: {self.recipient} ({self.status})>"

    def can_retry(self) -> bool:
        """Check if this message can be retried."""
        return self.retry_count < self.max_retries and self.status == "pending"

    def increment_retry(self) -> None:
        """Increment retry counter and update timestamp."""
        self.retry_count += 1
        self.last_attempt_at = datetime.now(timezone.utc)

    def mark_retried(self) -> None:
        """Mark this message as successfully retried."""
        self.status = "retried"
        self.retried_at = datetime.now(timezone.utc)

    def mark_abandoned(self) -> None:
        """Mark this message as abandoned after max retries."""
        self.status = "abandoned"
