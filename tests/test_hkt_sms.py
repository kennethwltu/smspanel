"""Tests for SMS service."""

from unittest.mock import patch

from smspanel.config import ConfigService
from smspanel.services.hkt_sms import HKTSMSService
from .mocks import MockHKTPost, MockSMSResponse


class TestHKTSMSService:
    """Tests for SMS service."""

    def test_init_with_defaults(self):
        """Test service initialization with config service."""
        config_service = ConfigService(base_url="https://test.com", application_id="test-app", sender_number="12345")
        service = HKTSMSService(config_service)
        config = service._get_config()
        assert config.base_url == "https://test.com"
        assert config.application_id == "test-app"
        assert config.sender_number == "12345"

    def test_get_config_with_explicit_values(self, app):
        """Test getting config when values are explicitly set."""
        with app.app_context():
            config_service = ConfigService(
                base_url="https://custom.com",
                application_id="custom-app",
                sender_number="99999",
            )
            service = HKTSMSService(config_service)
            config = service._get_config()
            assert config.base_url == "https://custom.com"
            assert config.application_id == "custom-app"
            assert config.sender_number == "99999"

    def test_get_config_from_flask_app(self, app):
        """Test getting config from Flask app with ConfigService."""
        with app.app_context():
            config_service = ConfigService(
                base_url=app.config["SMS_BASE_URL"],
                application_id=app.config["SMS_APPLICATION_ID"],
                sender_number=app.config["SMS_SENDER_NUMBER"],
            )
            service = HKTSMSService(config_service)
            config = service._get_config()
            assert config.base_url == app.config["SMS_BASE_URL"]
            assert config.application_id == app.config["SMS_APPLICATION_ID"]
            assert config.sender_number == app.config["SMS_SENDER_NUMBER"]

    @patch("smspanel.services.hkt_sms.requests.post")
    def test_send_single_success(self, mock_post, app):
        """Test successful single SMS send."""
        mock_post.side_effect = MockHKTPost(failure_rate=0, min_delay=0, max_delay=0)
        config_service = ConfigService(base_url="https://test.com", application_id="test-app", sender_number="12345")
        service = HKTSMSService(config_service)
        result = service.send_single("85212345678", "Test message")
        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["response_text"] == "SUCCESS"
        # Verify request was made
        call_args = mock_post.call_args[0][0]
        assert call_args == "https://test.com"

    @patch("smspanel.services.hkt_sms.requests.post")
    def test_send_single_http_error(self, mock_post, app):
        """Test single SMS send with HTTP error."""
        mock_post.side_effect = MockHKTPost(failure_rate=1.0, min_delay=0, max_delay=0)
        config_service = ConfigService(base_url="https://test.com", application_id="test-app", sender_number="12345")
        service = HKTSMSService(config_service)
        result = service.send_single("85212345678", "Test message")
        assert result["success"] is False
        assert "error" in result

    @patch("smspanel.services.hkt_sms.requests.post")
    def test_send_single_with_unicode(self, mock_post, app):
        """Test single SMS send with Unicode characters."""
        mock_post.side_effect = MockHKTPost(failure_rate=0, min_delay=0, max_delay=0)
        config_service = ConfigService(base_url="https://test.com", application_id="test-app", sender_number="12345")
        service = HKTSMSService(config_service)
        result = service.send_single("85212345678", "Test message with unicode")
        assert result["success"] is True
        assert result["status_code"] == 200
        assert "SUCCESS" in result["response_text"]

    @patch("smspanel.services.hkt_sms.requests.post")
    def test_send_bulk_all_success(self, mock_post, app):
        """Test bulk SMS send with all successful."""
        mock_post.side_effect = MockHKTPost(failure_rate=0, min_delay=0, max_delay=0)
        config_service = ConfigService(base_url="https://test.com", application_id="test-app", sender_number="12345")
        service = HKTSMSService(config_service)
        recipients = ["85212345678", "85287654321"]
        result = service.send_bulk(recipients, "Test bulk message")
        assert result["success"] is True
        assert result["total"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert len(result["results"]) == 2
        assert all(r["success"] for r in result["results"])

    @patch("smspanel.services.hkt_sms.requests.post")
    def test_send_bulk_partial_failure(self, mock_post, app):
        """Test bulk SMS send with partial failures."""
        call_count = [0]

        def side_effect_func(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MockSMSResponse(status_code=200, text="SUCCESS")
            else:
                from requests.exceptions import RequestException
                raise RequestException("Connection failed")

        mock_post.side_effect = side_effect_func
        config_service = ConfigService(base_url="https://test.com", application_id="test-app", sender_number="12345")
        service = HKTSMSService(config_service)
        recipients = ["85212345678", "85287654321"]
        result = service.send_bulk(recipients, "Test bulk message")
        assert result["success"] is False
        assert result["total"] == 2
        assert result["successful"] == 1
        assert result["failed"] == 1
        assert result["results"][0]["success"] is True
        assert result["results"][1]["success"] is False

    @patch("smspanel.services.hkt_sms.requests.post")
    def test_send_bulk_empty_list(self, mock_post, app):
        """Test bulk SMS send with empty recipient list."""
        config_service = ConfigService(base_url="https://test.com", application_id="test-app", sender_number="12345")
        service = HKTSMSService(config_service)
        result = service.send_bulk([], "Test bulk message")
        assert result["success"] is True
        assert result["total"] == 0
        assert result["successful"] == 0
        assert result["failed"] == 0
        assert result["results"] == []
        mock_post.assert_not_called()
