"""SMS service for sending SMS messages."""

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from typing import Dict, Optional

from smspanel.config import ConfigService, SMSConfig

# Request timeout in seconds for SMS gateway requests
SMS_REQUEST_TIMEOUT = 30


class SMSError(Exception):
    """Exception raised for SMS service errors."""

    pass


class HKTSMSService:
    """Service for interacting with SMS API."""

    def __init__(self, config_service: ConfigService):
        """Initialize SMS service.

        Args:
            config_service: Configuration service for SMS settings.
        """
        self.config_service = config_service
        self._config: Optional[SMSConfig] = None

    def _get_config(self) -> SMSConfig:
        """Get SMS configuration from config service."""
        if self._config is None:
            self._config = self.config_service.get_sms_config()
        return self._config

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
        reraise=True,
    )
    def send_single(self, recipient: str, message: str) -> Dict[str, any]:
        """Send a single SMS message with retry logic.

        Args:
            recipient: Phone number (e.g., "85212345678")
            message: SMS content (supports UTF-8)

        Returns:
            Dict with status and response details.

        Raises:
            SMSError: If API request fails after all retries.
        """
        config = self._get_config()

        data = {
            "application": config.application_id,
            "mrt": recipient,
            "sender": config.sender_number,
            "msg_utf8": message,
        }

        try:
            # Check if we're connecting to mock_sms service
            # If so, don't use proxy to avoid connection issues
            proxies = {}
            if "mock_sms" in config.base_url:
                # Explicitly disable proxy for mock_sms connections
                proxies = {"http": None, "https": None}
            
            response = requests.post(
                config.base_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=SMS_REQUEST_TIMEOUT,
                proxies=proxies,
            )

            response.raise_for_status()

            return {
                "success": True,
                "status_code": response.status_code,
                "response_text": response.text,
            }
        except (requests.ConnectionError, requests.Timeout):
            # Let tenacity handle retry
            raise
        except requests.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": getattr(getattr(e, "response", None), "status_code", None),
            }

    def send_bulk(self, recipients: list[str], message: str) -> Dict[str, any]:
        """Send SMS messages to multiple recipients.

        Args:
            recipients: List of phone numbers
            message: SMS content (supports UTF-8)

        Returns:
            Dict with overall status and individual results.
        """
        results = []

        for recipient in recipients:
            result = self.send_single(recipient, message)
            results.append(
                {
                    "recipient": recipient,
                    "success": result["success"],
                    "error": result.get("error"),
                    "response": result.get("response_text"),
                }
            )

        # Determine overall success
        all_success = all(r["success"] for r in results)

        return {
            "success": all_success,
            "total": len(recipients),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "results": results,
        }
