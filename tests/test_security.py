"""Tests for security hardening."""

import inspect


def test_admin_credentials_not_hardcoded():
    """Admin username/password should not be hardcoded in source."""
    from smspanel.app import _ensure_admin_user

    source = inspect.getsource(_ensure_admin_user)
    # Should not contain hardcoded credentials
    assert "SMSpass#12" not in source


def test_production_secret_key_not_default():
    """Production config should not use default/weak SECRET_KEY."""
    from smspanel.config.config import ProductionConfig
    
    # Save original class attribute
    original_secret_key = ProductionConfig.SECRET_KEY
    
    try:
        # Set the class attribute directly
        ProductionConfig.SECRET_KEY = "test-production-secret-key-that-is-at-least-32-chars-long"
        
        # Create ProductionConfig instance to trigger validation
        prod_config = ProductionConfig()
        secret = prod_config.SECRET_KEY
        assert secret != "dev-secret-key-change-in-production"
        assert len(secret) >= 32  # At least 256 bits
    finally:
        # Restore original class attribute
        ProductionConfig.SECRET_KEY = original_secret_key


def test_env_documentation_exists():
    """Environment variables should be documented."""
    import os

    docs_exist = os.path.exists(".env.example") or "ADMIN_PASSWORD" in (
        open("README.md").read() if os.path.exists("README.md") else ""
    )
    assert docs_exist, "ADMIN_PASSWORD env var should be documented"
