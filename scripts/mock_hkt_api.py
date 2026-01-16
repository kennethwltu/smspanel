#!/usr/bin/env python3
"""Mock HKT SMS service provider API for testing.

This script runs a simple Flask server that mimics the HKT SMS API
endpoint for testing purposes without needing real HKT credentials.

Usage:
    python scripts/mock_hkt_api.py

Then in your application, set HKT_BASE_URL to the mock server URL:
    HKT_BASE_URL=http://localhost:5555/gateway/gateway.jsp
"""

from flask import Flask, request, jsonify
import os

app = Flask(__name__)


@app.route("/gateway/gateway.jsp", methods=["POST"])
def mock_hkt_gateway():
    """Mock HKT SMS gateway endpoint.

    Accepts form data with:
        - application: Application ID
        - mrt: Mobile Recipient Number (e.g., "85212345678")
        - sender: Sender number
        - msg_utf8: Message content (UTF-8 encoded)

    Returns:
        Mock HKT API response
    """
    data = request.form
    application = data.get("application", "")
    mrt = data.get("mrt", "")
    sender = data.get("sender", "")
    msg_utf8 = data.get("msg_utf8", "")

    # Dump message content to stdout
    print(f"[Mock HKT] Message: {msg_utf8}")

    # Return 401 if "error" is in the message
    if "error" in msg_utf8.lower():
        return "401 Unauthorized", 401

    # Return 200 OK for normal requests
    return "200 OK", 200


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "mock-hkt-api"}), 200


if __name__ == "__main__":
    # Use port 5555 to avoid conflicts with main app (port 5000)
    port = int(os.getenv("MOCK_HKT_PORT", "5555"))
    host = os.getenv("MOCK_HKT_HOST", "127.0.0.1")
    debug = os.getenv("MOCK_HKT_DEBUG", "false").lower() == "true"

    print(f"Starting Mock HKT SMS API on http://{host}:{port}")
    print(f"Gateway endpoint: http://{host}:{port}/gateway/gateway.jsp")
    print(f"Health check: http://{host}:{port}/health")

    app.run(host=host, port=port, debug=debug)
