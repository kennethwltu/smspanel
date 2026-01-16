"""Tests for HKT SMS service."""

import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import RequestException

from ccdemo import create_app
from ccdemo.services.hkt_sms import HKTSMSService, HKTSMSError


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

    @patch("app.services.hkt_sms.requests.post")
    def test_send_single_success(self, mock_post, app):
        """Test successful single SMS send."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "SUCCESS"
        mock_post.return_value = mock_response

        with app.app_context():
            service = HKTSMSService("https://test.com", "test-app", "12345")
            result = service.send_single("85212345678", "Test message")

            assert result["success"] is True
            assert result["status_code"] == 200
            assert result["response_text"] == "SUCCESS"

            # Verify the request was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://test.com"
            assert call_args[1]["data"]["application"] == "test-app"
            assert call_args[1]["data"]["mrt"] == "85212345678"
            assert call_args[1]["data"]["sender"] == "12345"
            assert call_args[1]["data"]["msg_utf8"] == "Test message"

    @patch("app.services.hkt_sms.requests.post")
    def test_send_single_http_error(self, mock_post, app):
        """Test single SMS send with HTTP error."""
        mock_post.side_effect = RequestException("Connection failed")

        with app.app_context():
            service = HKTSMSService("https://test.com", "test-app", "12345")
            result = service.send_single("85212345678", "Test message")

            assert result["success"] is False
            assert "error" in result
            assert "Connection failed" in result["error"]

    @patch("app.services.hkt_sms.requests.post")
    def test_send_single_with_unicode(self, mock_post, app):
        """Test single SMS send with Unicode characters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "SUCCESS"
        mock_post.return_value = mock_response

        with app.app_context():
            service = HKTSMSService("https://test.com", "test-app", "12345")
            result = service.send_single("85212345678", "这是一条中文测试短信")

            assert result["success"] is True

            # Verify the Unicode was sent correctly
            call_args = mock_post.call_args
            assert call_args[1]["data"]["msg_utf8"] == "这是一条中文测试短信"

    @patch("app.services.hkt_sms.requests.post")
    def test_send_bulk_all_success(self, mock_post, app):
        """Test bulk SMS send with all successful."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "SUCCESS"
        mock_post.return_value = mock_response

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

    @patch("app.services.hkt_sms.requests.post")
    def test_send_bulk_partial_failure(self, mock_post, app):
        """Test bulk SMS send with partial failures."""
        # First call succeeds, second fails
        mock_post.side_effect = [
            MagicMock(status_code=200, text="SUCCESS"),
            RequestException("Connection failed"),
        ]

        with app.app_context():
            service = HKTSMSService("https://test.com", "test-app", "12345")
            recipients = ["85212345678", "85287654321"]
            result = service.send_bulk(recipients, "Test bulk message")

            assert result["success"] is False  # Overall is False since not all succeeded
            assert result["total"] == 2
            assert result["successful"] == 1
            assert result["failed"] == 1
            assert result["results"][0]["success"] is True
            assert result["results"][1]["success"] is False

    @patch("app.services.hkt_sms.requests.post")
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
