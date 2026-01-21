"""Tests for retry logic."""

from unittest.mock import patch, MagicMock
from requests.exceptions import ConnectionError


def test_tenacity_available():
    """Tenacity library should be available for retry logic."""
    import tenacity

    assert tenacity is not None
    # Check version has retry decorator
    assert hasattr(tenacity, "retry")
    assert hasattr(tenacity, "stop_after_attempt")
    assert hasattr(tenacity, "wait_exponential")


def test_send_single_retries_on_connection_error(app):
    """send_single should retry on connection errors."""
    from smspanel.config import ConfigService
    from smspanel.services.hkt_sms import HKTSMSService

    call_count = []

    def mock_post(*args, **kwargs):
        call_count.append(args)
        if len(call_count) < 3:
            raise ConnectionError("Simulated connection error")
        return MagicMock(status_code=200, text="SUCCESS", raise_for_status=MagicMock())

    with patch("smspanel.services.hkt_sms.requests.post", side_effect=mock_post):
        config_service = ConfigService(
            base_url="https://test.com", application_id="test-app", sender_number="12345"
        )
        service = HKTSMSService(config_service)
        result = service.send_single("85212345678", "Test message")

        # Should succeed after retries
        assert result["success"] is True
        # Should have called post 3 times (2 failures + 1 success)
        assert len(call_count) == 3
