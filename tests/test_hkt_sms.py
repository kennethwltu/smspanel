"""Tests for HKT SMS service."""

from unittest.mock import patch

from ccdemo.services.hkt_sms import HKTSMSService
from .mocks import MockHKTPost, MockHKTResponse


class TestHKTSMSService:
    """Tests for HKT SMS service."""

    def test_init_with_defaults(self):
        """Test service initialization with default values."""
        service = HKTSMSService("https://test.com", "test-app", "12345")
        assert service.base_url == "https://test.com"
        assert service.application_id == "test-app"
        assert service.sender_number == "12345"

    def test_get_config_with_explicit_values(self, app):
        """Test getting config when values are explicitly set."""
        with app.app_context():
            service = HKTSMSService("https://custom.com", "custom-app", "99999")
            config = service._get_config()
            assert config["base_url"] == "https://custom.com"
            assert config["application_id"] == "custom-app"
            assert config["sender_number"] == "99999"

    def test_get_config_from_flask_app(self, app):
        """Test getting config from Flask app when not explicitly set."""
        with app.app_context():
            service = HKTSMSService()
            config = service._get_config()
            assert config["base_url"] == app.config["HKT_BASE_URL"]
            assert config["application_id"] == app.config["HKT_APPLICATION_ID"]
            assert config["sender_number"] == app.config["HKT_SENDER_NUMBER"]

    @patch("ccdemo.services.hkt_sms.requests.post")
    def test_send_single_success(self, mock_post, app):
        """Test successful single SMS send."""
        mock_post.side_effect = MockHKTPost(failure_rate=0, min_delay=0, max_delay=0)

        with app.app_context():
            service = HKTSMSService("https://test.com", "test-app", "12345")
            result = service.send_single("85212345678", "Test message")

            assert result["success"] is True
            assert result["status_code"] == 200
            assert result["response_text"] == "SUCCESS"

            # Verify the request was made
            call_args = mock_post.call_args[0][0]
            assert call_args == "https://test.com"

    @patch("ccdemo.services.hkt_sms.requests.post")
    def test_send_single_http_error(self, mock_post, app):
        """Test single SMS send with HTTP error."""
        mock_post.side_effect = MockHKTPost(failure_rate=1.0, min_delay=0, max_delay=0)

        with app.app_context():
            service = HKTSMSService("https://test.com", "test-app", "12345")
            result = service.send_single("85212345678", "Test message")

            assert result["success"] is False
            assert "error" in result

    @patch("ccdemo.services.hkt_sms.requests.post")
    def test_send_single_with_unicode(self, mock_post, app):
        """Test single SMS send with Unicode characters."""
        mock_post.side_effect = MockHKTPost(failure_rate=0, min_delay=0, max_delay=0)

        with app.app_context():
            service = HKTSMSService("https://test.com", "test-app", "12345")
            result = service.send_single("85212345678", "这是一条中文测试短信")

            assert result["success"] is True

    @patch("ccdemo.services.hkt_sms.requests.post")
    def test_send_bulk_all_success(self, mock_post, app):
        """Test bulk SMS send with all successful."""
        mock_post.side_effect = MockHKTPost(failure_rate=0, min_delay=0, max_delay=0)

        with app.app_context():
            service = HKTSMSService("https://test.com", "test-app", "12345")
            recipients = ["85212345678", "85287654321"]
            result = service.send_bulk(recipients, "Test bulk message")

            assert result["success"] is True
            assert result["total"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0
            assert len(result["results"]) == 2
            assert all(r["success"] for r in result["results"])

    @patch("ccdemo.services.hkt_sms.requests.post")
    def test_send_bulk_partial_failure(self, mock_post, app):
        """Test bulk SMS send with partial failures."""
        # Track call count and behave differently on each call
        call_count = [0]

        def side_effect_func(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call succeeds
                return MockHKTResponse(status_code=200, text="SUCCESS")
            else:
                # Second call fails
                from requests.exceptions import RequestException
                raise RequestException("Connection failed")

        mock_post.side_effect = side_effect_func

        with app.app_context():
            service = HKTSMSService("https://test.com", "test-app", "12345")
            recipients = ["85212345678", "85287654321"]
            result = service.send_bulk(recipients, "Test bulk message")

            assert result["success"] is False
            assert result["total"] == 2
            assert result["successful"] == 1
            assert result["failed"] == 1
            assert result["results"][0]["success"] is True
            assert result["results"][1]["success"] is False

    @patch("ccdemo.services.hkt_sms.requests.post")
    def test_send_bulk_empty_list(self, mock_post, app):
        """Test bulk SMS send with empty recipient list."""
        with app.app_context():
            service = HKTSMSService("https://test.com", "test-app", "12345")
            result = service.send_bulk([], "Test bulk message")

            assert result["success"] is True
            assert result["total"] == 0
            assert result["successful"] == 0
            assert result["failed"] == 0
            assert result["results"] == []
            mock_post.assert_not_called()
