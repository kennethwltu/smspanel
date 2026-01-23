#!/usr/bin/env python
"""Initialize the database."""

import os
import sys

# Add the src directory to the Python path so we can import smspanel
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from smspanel import create_app, db

app = create_app()

# Get database URL from config
db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
print(f"Database URL: {db_url}")

with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully.")
        
        # Create admin user if it doesn't exist
        from smspanel.models import User
        admin_user = User.query.filter_by(username="SMSadmin").first()
        if admin_user is None:
            admin = User(username="SMSadmin")
            admin.set_password("SMSpass#12")
            admin.token = User.generate_token()
            admin.is_admin = True
            admin.is_active = True

            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully.")
    except Exception as e:
        print(f"Error creating database: {e}")
        print("\nNote: The app configuration automatically checks if the database directory is writable.")
        print("If the instance directory is not writable, it will use /tmp/sms.db instead.")
        print("You can also manually set DATABASE_URL environment variable to use a different location.")
        raise
