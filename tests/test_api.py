"""Tests for API endpoints."""

import json
import pytest
from ccdemo import db
from ccdemo.models import User, Message, Recipient


class TestAuthAPI:
    """Tests for authentication API endpoints."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == 200
        data = response.json
        assert "access_token" in data
        assert data["username"] == "testuser"
        assert data["user_id"] == test_user.id

    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrongpass"},
        )
        assert response.status_code == 401
        assert "error" in response.json

    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser"},
        )
        assert response.status_code == 400

    def test_logout(self, client, auth_headers):
        """Test logout endpoint."""
        response = client.post("/api/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert "message" in response.json


class TestSMSAPI:
    """Tests for SMS API endpoints."""

    def test_list_messages_unauthorized(self, client):
        """Test listing messages without authorization."""
        response = client.get("/api/sms")
        assert response.status_code == 401

    def test_list_messages_empty(self, client, auth_headers, test_user):
        """Test listing messages when user has none."""
        # Delete the fixture message
        Message.query.delete()
        Recipient.query.delete()
        db.session.commit()

        response = client.get("/api/sms", headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert "messages" in data
        assert data["total"] == 0
        assert data["messages"] == []

    def test_list_messages_with_data(self, client, auth_headers, test_message):
        """Test listing messages with existing data."""
        response = client.get("/api/sms", headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert data["total"] >= 1
        assert len(data["messages"]) >= 1

    def test_send_sms_unauthorized(self, client):
        """Test sending SMS without authorization."""
        response = client.post(
            "/api/sms",
            json={"recipient": "85212345678", "content": "Test"},
        )
        assert response.status_code == 401

    def test_send_sms_missing_fields(self, client, auth_headers):
        """Test sending SMS with missing fields."""
        response = client.post("/api/sms", json={"recipient": "85212345678"}, headers=auth_headers)
        assert response.status_code == 400

    def test_send_sms_invalid_request(self, client, auth_headers):
        """Test sending SMS to HKT (will fail without actual HKT credentials)."""
        response = client.post(
            "/api/sms",
            json={"recipient": "85212345678", "content": "Test message"},
            headers=auth_headers,
        )
        # Should still create the record, but HKT send will fail
        assert response.status_code in [200, 500]
        data = response.json
        assert "id" in data

    def test_send_bulk_sms_unauthorized(self, client):
        """Test sending bulk SMS without authorization."""
        response = client.post(
            "/api/sms/send-bulk",
            json={"recipients": ["85212345678"], "content": "Test"},
        )
        assert response.status_code == 401

    def test_send_bulk_sms_missing_fields(self, client, auth_headers):
        """Test sending bulk SMS with missing fields."""
        response = client.post("/api/sms/send-bulk", json={"recipients": ["85212345678"]}, headers=auth_headers)
        assert response.status_code == 400

    def test_get_message_unauthorized(self, client, test_message):
        """Test getting message details without authorization."""
        response = client.get(f"/api/sms/{test_message.id}")
        assert response.status_code == 401

    def test_get_message_not_found(self, client, auth_headers):
        """Test getting non-existent message."""
        response = client.get("/api/sms/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_message_success(self, client, auth_headers, test_message):
        """Test getting message details successfully."""
        response = client.get(f"/api/sms/{test_message.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert data["id"] == test_message.id
        assert data["content"] == test_message.content

    def test_get_message_recipients_unauthorized(self, client, test_message):
        """Test getting message recipients without authorization."""
        response = client.get(f"/api/sms/{test_message.id}/recipients")
        assert response.status_code == 401

    def test_get_message_recipients_success(self, client, auth_headers, test_message):
        """Test getting message recipients successfully."""
        response = client.get(f"/api/sms/{test_message.id}/recipients", headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert "recipients" in data
        assert len(data["recipients"]) >= 1
