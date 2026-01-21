"""Tests for dead letter queue."""
import pytest


def test_dead_letter_message_model_exists():
    """DeadLetterMessage model should exist."""
    from smspanel.models import DeadLetterMessage

    assert DeadLetterMessage is not None
    # Check required columns
    assert hasattr(DeadLetterMessage, "id")
    assert hasattr(DeadLetterMessage, "message_id")
    assert hasattr(DeadLetterMessage, "recipient")
    assert hasattr(DeadLetterMessage, "content")
    assert hasattr(DeadLetterMessage, "error_message")
    assert hasattr(DeadLetterMessage, "retry_count")
    assert hasattr(DeadLetterMessage, "created_at")


def test_dead_letter_service_exists(app):
    """DeadLetterQueue service should exist."""
    from smspanel.services.dead_letter import DeadLetterQueue

    with app.app_context():
        dlq = DeadLetterQueue()
        assert dlq is not None


def test_dead_letter_queue_add(app):
    """DeadLetterQueue should be able to add failed messages."""
    from smspanel.services.dead_letter import DeadLetterQueue
    from smspanel.models import DeadLetterMessage

    with app.app_context():
        db.create_all()
        dlq = DeadLetterQueue()
        dlq.add(
            message_id=1,
            recipient="85212345678",
            content="Test message",
            error_message="Connection timeout",
            error_type="Timeout",
        )

        # Verify message was added
        count = DeadLetterMessage.query.count()
        assert count == 1

        # Verify message details
        msg = DeadLetterMessage.query.first()
        assert msg.recipient == "85212345678"
        assert msg.content == "Test message"
        assert msg.error_message == "Connection timeout"
        assert msg.status == "pending"


def test_dead_letter_admin_routes_exist(app):
    """Admin routes for dead letter should exist."""
    from smspanel.web.dead_letter import web_dead_letter_bp

    assert web_dead_letter_bp is not None

    # Check route registration
    routes = [rule.rule for rule in web_dead_letter_bp.url_map.iter_rules()]
    assert "/admin/dead-letter" in routes
    assert "/admin/dead-letter/retry" in routes
    assert "/admin/dead-letter/abandon" in routes
