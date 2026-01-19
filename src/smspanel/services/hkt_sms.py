"""HKT SMS service for sending SMS messages."""

import requests
from flask import current_app
from typing import Dict, Optional


class HKTSMSError(Exception):
    """Exception raised for HKT SMS service errors."""

    pass


class HKTSMSService:
    """Service for interacting with HKT SMS API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        application_id: Optional[str] = None,
        sender_number: Optional[str] = None,
    ):
        """Initialize the HKT SMS service.

        Args:
            base_url: HKT API base URL. If None, uses Flask app config.
            application_id: HKT application ID. If None, uses Flask app config.
            sender_number: HKT sender number. If None, uses Flask app config.
        """
        self.base_url = base_url
        self.application_id = application_id
        self.sender_number = sender_number

    def _get_config(self) -> Dict[str, str]:
        """Get configuration from Flask app if not set."""
        if self.base_url is None:
            self.base_url = current_app.config.get(
                "HKT_BASE_URL", "https://cst01.1010.com.hk/gateway/gateway.jsp"
            )
        if self.application_id is None:
            self.application_id = current_app.config.get("HKT_APPLICATION_ID", "LabourDept")
        if self.sender_number is None:
            self.sender_number = current_app.config.get("HKT_SENDER_NUMBER", "852520702793127")

        return {
            "base_url": self.base_url,
            "application_id": self.application_id,
            "sender_number": self.sender_number,
        }

    def send_single(self, recipient: str, message: str) -> Dict[str, any]:
        """Send a single SMS message.

        Args:
            recipient: Phone number (e.g., "85212345678")
            message: SMS content (supports UTF-8)

        Returns:
            Dict with status and response details.

        Raises:
            HKTSMSError: If the API request fails.
        """
        config = self._get_config()

        data = {
            "application": config["application_id"],
            "mrt": recipient,
            "sender": config["sender_number"],
            "msg_utf8": message,
        }

        try:
            response = requests.post(
                config["base_url"],
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )

            response.raise_for_status()

            return {
                "success": True,
                "status_code": response.status_code,
                "response_text": response.text,
            }

        except requests.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": getattr(e.response, "status_code", None)
                if hasattr(e, "response")
                else None,
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
