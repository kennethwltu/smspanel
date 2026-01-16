"""Pytest configuration and fixtures."""

import pytest
import uuid
from ccdemo import create_app, db
from ccdemo.models import User, Message, Recipient


@pytest.fixture(scope="function")
def app():
    """Create and configure a test application instance."""
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for app's Click commands."""
    return app.test_cli_runner()


def _create_test_user(app, username="testuser", password="testpass123"):
    """Helper to create a test user."""
    with app.app_context():
        # Use unique username if default is taken
        existing = User.query.filter_by(username=username).first()
        if existing:
            username = f"{username}_{uuid.uuid4().hex[:8]}"

        user = User(username=username)
        user.set_password(password)
        user.api_key = f"test-api-key-{uuid.uuid4().hex[:16]}"
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        stored_username = username
        db.session.expunge(user)
        return user_id, stored_username


@pytest.fixture
def test_user(app):
    """Create a test user and return a simple object."""
    user_id, username = _create_test_user(app)
    return type('TestUser', (), {'id': user_id, 'username': username})()


@pytest.fixture
def auth_headers(client, app):
    """Get JWT auth headers for a test user."""
    user_id, username = _create_test_user(app)
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "testpass123"},
    )
    token = response.json["access_token"]
    return {"Authorization": f"Bearer {token}", "user_id": user_id}


@pytest.fixture
def test_message(app):
    """Create a test user and message, return a simple object."""
    with app.app_context():
        # Create user with unique username
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        user = User(username=username)
        user.set_password("testpass123")
        user.api_key = f"test-api-key-{uuid.uuid4().hex[:16]}"
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        # Create message
        message = Message(user_id=user_id, content="Test message", status="sent")
        db.session.add(message)
        db.session.flush()

        recipient = Recipient(message_id=message.id, phone="85212345678", status="sent")
        db.session.add(recipient)
        db.session.commit()
        message_id = message.id
        # Return simple object with id and content attributes
        return type('TestMessage', (), {'id': message_id, 'content': 'Test message'})()
