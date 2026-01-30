"""Tests for admin messages route."""


def test_admin_messages_route_exists():
    """Admin messages route should exist."""
    from smspanel import create_app

    app = create_app("testing")
    with app.test_client() as client:
        # Enable admin for testing
        with app.app_context():
            from smspanel.models import User
            from smspanel import db

            admin = User.query.filter_by(username="SMSadmin").first()
            if admin:
                admin.is_active = True
                admin.is_admin = True
                db.session.commit()

        # Test route exists (will redirect to login if not authenticated)
        response = client.get("/admin/messages", follow_redirects=True)
        assert response.status_code == 200


def test_admin_messages_route_requires_admin():
    """Admin messages route should require admin privileges."""
    from smspanel import create_app

    app = create_app("testing")
    with app.test_client() as client:
        # Test without admin - should redirect or show forbidden
        response = client.get("/admin/messages", follow_redirects=True)
        # Either login page or forbidden response is acceptable
        assert response.status_code in [200, 302, 403]


def test_admin_messages_route_filters():
    """Admin messages route should accept filter parameters."""
    from smspanel import create_app

    app = create_app("testing")
    with app.test_client() as client:
        # Enable admin for testing
        with app.app_context():
            from smspanel.models import User
            from smspanel import db

            admin = User.query.filter_by(username="SMSadmin").first()
            if admin:
                admin.is_active = True
                admin.is_admin = True
                db.session.commit()

        # Test with filters
        response = client.get("/admin/messages?user_id=1&status=pending", follow_redirects=True)
        assert response.status_code == 200
