"""Tests for standardized error response format."""


def test_error_response_has_nested_format(app):
    """Error responses should use nested {error: {...}} format."""
    from smspanel.api.responses import APIResponse

    with app.app_context():
        # Test error response format
        response, status = APIResponse.error("Test error", 400, "TEST_ERROR")
        data = response.get_json()

        # New format: {"error": {"code": "TEST_ERROR", "message": "Test error"}}
        assert "error" in data
        assert isinstance(data["error"], dict)
        assert data["error"]["code"] == "TEST_ERROR"
        assert data["error"]["message"] == "Test error"
        assert "success" not in data  # No success field in error response


def test_success_response_unchanged(app):
    """Success responses should remain unchanged."""
    from smspanel.api.responses import APIResponse

    with app.app_context():
        response, status = APIResponse.success({"key": "value"}, "Success", 200)
        data = response.get_json()

        assert data["success"] is True
        assert data["data"] == {"key": "value"}
        assert data["message"] == "Success"


def test_unauthorized_error_format(app):
    """Unauthorized error should use nested format."""
    from smspanel.api.responses import unauthorized

    with app.app_context():
        response, status = unauthorized("Token expired", "TOKEN_EXPIRED")
        data = response.get_json()

        assert status == 401
        assert "error" in data
        assert data["error"]["code"] == "TOKEN_EXPIRED"
        assert data["error"]["message"] == "Token expired"


def test_bad_request_error_format(app):
    """Bad request error should use nested format."""
    from smspanel.api.responses import bad_request

    with app.app_context():
        response, status = bad_request("Missing field", "MISSING_FIELD")
        data = response.get_json()

        assert status == 400
        assert "error" in data
        assert data["error"]["code"] == "MISSING_FIELD"
        assert data["error"]["message"] == "Missing field"


def test_not_found_error_format(app):
    """Not found error should use nested format."""
    from smspanel.api.responses import not_found

    with app.app_context():
        response, status = not_found("Resource not found", "NOT_FOUND")
        data = response.get_json()

        assert status == 404
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"


def test_service_unavailable_error_format(app):
    """Service unavailable error should use nested format."""
    from smspanel.api.responses import service_unavailable

    with app.app_context():
        response, status = service_unavailable("Queue full", "QUEUE_FULL")
        data = response.get_json()

        assert status == 503
        assert "error" in data
        assert data["error"]["code"] == "QUEUE_FULL"


def test_internal_server_error_format(app):
    """Internal server error should use nested format."""
    from smspanel.api.responses import internal_server_error

    with app.app_context():
        response, status = internal_server_error("Unexpected error", "INTERNAL_ERROR")
        data = response.get_json()

        assert status == 500
        assert "error" in data
        assert data["error"]["code"] == "INTERNAL_ERROR"
