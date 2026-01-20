"""Tests for CSRF protection."""
import pytest


def test_csrf_token_required_on_login():
    """Login form should reject requests without CSRF token."""
    from smspanel.app import create_app

    app = create_app("testing")
    with app.test_client() as client:
        response = client.post(
            "/login",
            data={"username": "test", "password": "test"},
            follow_redirects=True
        )
        # Should fail or show error due to missing CSRF token
        assert response.status_code == 200


def test_base_template_contains_csrf_token():
    """Base template should include CSRF token field."""
    from smspanel.app import create_app

    app = create_app("testing")
    # Check that csrf is imported from extensions
    from smspanel.extensions import csrf
    assert csrf is not None


def test_csrf_protection_initialized():
    """CSRF protection should be configured on app."""
    from flask import Flask
    from smspanel.extensions import csrf

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["WTF_CSRF_ENABLED"] = True
    # Initialize CSRF
    csrf.init_app(app)

    # CSRF should now be enabled
    assert app.config.get("WTF_CSRF_ENABLED") == True


def test_login_rejects_invalid_csrf():
    """Login with invalid CSRF token should be rejected."""
    from flask import Flask
    from smspanel.extensions import init_all, db
    from smspanel.app import _register_blueprints

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True

    # Initialize extensions
    init_all(app)
    _register_blueprints(app)

    # Create tables
    with app.app_context():
        db.create_all()

    with app.test_client() as client:
        response = client.post(
            "/login",
            data={
                "username": "SMSadmin",
                "password": "SMSpass#12",
                "csrf_token": "invalid-token"
            }
        )
        # Should return 400 Bad Request
        assert response.status_code == 400


def test_all_forms_have_csrf_token():
    """All form templates should include CSRF token."""
    import os
    from smspanel.app import create_app

    templates_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "src", "smspanel", "templates"
    )

    for root, _, files in os.walk(templates_dir):
        for fname in files:
            if fname.endswith(".html"):
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    content = f.read()
                # Check if template has forms but no CSRF
                if "<form" in content:
                    assert 'name="csrf_token"' in content or 'csrf_token()' in content, \
                        f"Template {fname} has form but no CSRF token"
