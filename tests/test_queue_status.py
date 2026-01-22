"""Tests for the queue status API endpoint."""


def test_queue_status_endpoint_exists(app):
    """Queue status endpoint should return queue statistics."""
    with app.test_client() as client:
        response = client.get("/api/queue/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "queue_depth" in data["data"]
        assert "msgs_per_sec" in data["data"]
        assert "pending_messages" in data["data"]
        assert "sending_messages" in data["data"]
        assert "oldest_pending_at" in data["data"]
