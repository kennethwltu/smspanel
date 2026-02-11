"""Tests for API endpoints."""

from smspanel import db
from smspanel.models import Message, Recipient


class TestSMSAPI:
    """Tests for SMS API endpoints."""

    def test_list_messages_unauthorized(self, client):
        """Test listing messages without authorization."""
        response = client.get("/api/sms")
        assert response.status_code == 401

    def test_list_messages_empty(self, client, auth_headers, test_user):
        """Test listing messages when user has none."""
        # Delete fixture message
        Message.query.delete()
        Recipient.query.delete()
        db.session.commit()

        response = client.get("/api/sms", headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert "messages" in data["data"]
        assert data["data"]["total"] == 0
        assert data["data"]["messages"] == []

    def test_list_messages_with_data(self, client, auth_headers, test_message):
        """Test listing messages with existing data."""
        response = client.get("/api/sms", headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["data"]["total"] >= 1
        assert len(data["data"]["messages"]) >= 1

    def test_send_sms_unauthorized(self, client):
        """Test sending SMS without authorization."""
        response = client.post(
            "/api/sms",
            json={"recipient": "+85212345678", "content": "Test"},
        )
        assert response.status_code == 401
        data = response.json
        assert "error" in data
        assert isinstance(data["error"], dict)
        assert "code" in data["error"]

    def test_send_sms_missing_fields(self, client, auth_headers):
        """Test sending SMS with missing fields."""
        response = client.post("/api/sms", json={"recipient": "+85212345678"}, headers=auth_headers)
        assert response.status_code == 400
        data = response.json
        assert "error" in data
        assert isinstance(data["error"], dict)
        assert "code" in data["error"]

    def test_send_sms_invalid_request(self, client, auth_headers):
        """Test sending SMS to HKT (will be queued)."""
        response = client.post(
            "/api/sms",
            json={"recipient": "+85212345678", "content": "Test message"},
            headers=auth_headers,
        )
        # SMS should be queued and return 202
        assert response.status_code == 202
        data = response.json
        assert data["success"] is True
        assert "id" in data["data"]
        assert data["data"]["status"] == "pending"

    def test_send_bulk_sms_unauthorized(self, client):
        """Test sending bulk SMS without authorization."""
        response = client.post(
            "/api/sms/send-bulk",
            json={"recipients": ["+85212345678"], "content": "Test"},
        )
        assert response.status_code == 401

    def test_send_bulk_sms_missing_fields(self, client, auth_headers):
        """Test sending bulk SMS with missing fields."""
        response = client.post(
            "/api/sms/send-bulk", json={"recipients": ["+85212345678"]}, headers=auth_headers
        )
        assert response.status_code == 400
        data = response.json
        assert "error" in data
        assert isinstance(data["error"], dict)
        assert "code" in data["error"]

    def test_get_message_unauthorized(self, client, test_message):
        """Test getting message details without authorization."""
        response = client.get(f"/api/sms/{test_message.id}")
        assert response.status_code == 401

    def test_get_message_not_found(self, client, auth_headers):
        """Test getting non-existent message."""
        response = client.get("/api/sms/99999", headers=auth_headers)
        assert response.status_code == 404
        data = response.json
        assert "error" in data
        assert isinstance(data["error"], dict)
        assert "code" in data["error"]

    def test_get_message_success(self, client, auth_headers, test_message):
        """Test getting message details successfully."""
        response = client.get(f"/api/sms/{test_message.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["data"]["id"] == test_message.id
        assert data["data"]["content"] == test_message.content

    def test_get_message_recipients_unauthorized(self, client, test_message):
        """Test getting message recipients without authorization."""
        response = client.get(f"/api/sms/{test_message.id}/recipients")
        assert response.status_code == 401

    def test_get_message_recipients_success(self, client, auth_headers, test_message):
        """Test getting message recipients successfully."""
        response = client.get(f"/api/sms/{test_message.id}/recipients", headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert "recipients" in data["data"]
        assert len(data["data"]["recipients"]) >= 1
