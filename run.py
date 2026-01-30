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
    # Bind to 0.0.0.0 to make it accessible from outside the container
    # Use localhost only in development for security
    app.run(host="0.0.0.0", port=3570, debug=True)
