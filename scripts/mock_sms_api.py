#!/usr/bin/env python3
"""Mock SMS service provider API for testing.

This script runs a simple Flask server that mimics SMS API
endpoint for testing purposes without needing real SMS credentials.

Usage:
    python scripts/mock_sms_api.py

Then in your application, set SMS_BASE_URL to the mock server URL:
    SMS_BASE_URL=http://localhost:5555/gateway/gateway.jsp
"""

from flask import Flask, request, jsonify
import os

app = Flask(__name__)


@app.route("/gateway/gateway.jsp", methods=["POST"])
def mock_sms_gateway():
    """Mock SMS gateway endpoint.

    Accepts form data with:
        - msg_utf8: Message content (UTF-8 encoded)

    Returns:
        Mock SMS API response
    """
    data = request.form
    msg_utf8 = data.get("msg_utf8", "")

    # Dump message content to stdout
    print(f"[Mock SMS] Message: {msg_utf8}")

    # Return 401 if "error" is in the message
    if "error" in msg_utf8.lower():
        return "401 Unauthorized", 401

    # Return 200 OK for normal requests
    return "200 OK", 200


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "mock-sms-api"}), 200


if __name__ == "__main__":
    # Use port 5555 to avoid conflicts with main app (port 5000)
    port = int(os.getenv("MOCK_SMS_PORT", "5555"))
    host = os.getenv("MOCK_SMS_HOST", "127.0.0.1")
    debug = os.getenv("MOCK_SMS_DEBUG", "false").lower() == "true"

    print(f"Starting Mock SMS API on http://{host}:{port}")
    print(f"Gateway endpoint: http://{host}:{port}/gateway/gateway.jsp")
    print(f"Health check: http://{host}:{port}/health")

    app.run(host='0.0.0.0', port=port, debug=debug)
