"""Entry point for running the Flask application."""

import os
import sys

# Add the src directory to the Python path so we can import smspanel
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from smspanel import create_app  # noqa: E402

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    port = int(os.getenv("SMSPANEL_PORT", "3570"))
    host = os.getenv("SMSPANEL_HOST", "127.0.0.1")
    debug = os.getenv("SMSPANEL_DEBUG", "false").lower() == "true"

    print(f"Starting sms panel on http://{host}:{port}")
    
    app.run(host=host, port=port, debug=debug)
