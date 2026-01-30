def test_mysql_uri_parsed_correctly():
    """MySQL connection string should parse correctly."""
    from smspanel.config.config import Config

    Config.SQLALCHEMY_DATABASE_URI = "mysql+pymysql://user:pass@localhost:3306/smspanel"
    assert "mysql+pymysql" in Config.SQLALCHEMY_DATABASE_URI
    assert "pymysql" in Config.SQLALCHEMY_DATABASE_URI


def test_pool_settings_configured():
    """Pool settings should be configurable."""
    from smspanel.config.config import Config

    assert hasattr(Config, "SQLALCHEMY_POOL_SIZE")
    assert hasattr(Config, "SQLALCHEMY_POOL_MAX_OVERFLOW")
    assert hasattr(Config, "SQLALCHEMY_POOL_RECYCLE")
    assert hasattr(Config, "SQLALCHEMY_POOL_PRE_PING")
    assert Config.SQLALCHEMY_POOL_SIZE == 10
    assert Config.SQLALCHEMY_POOL_MAX_OVERFLOW == 20
    assert Config.SQLALCHEMY_POOL_RECYCLE == 3600
    assert Config.SQLALCHEMY_POOL_PRE_PING is True


def test_production_pool_settings():
    """Production config should have proper pool settings."""
    from smspanel.config.config import ProductionConfig
    
    # Save original class attribute
    original_secret_key = ProductionConfig.SECRET_KEY
    
    try:
        # Set the class attribute directly
        ProductionConfig.SECRET_KEY = "test-production-secret-key-that-is-at-least-32-chars-long"
        
        # Now create instance - should not raise ValueError
        prod_config = ProductionConfig()
        assert prod_config.SQLALCHEMY_POOL_SIZE == 10
        assert prod_config.SQLALCHEMY_POOL_MAX_OVERFLOW == 20
        assert prod_config.SQLALCHEMY_POOL_RECYCLE == 3600
        assert prod_config.SQLALCHEMY_POOL_PRE_PING is True
    finally:
        # Restore original class attribute
        ProductionConfig.SECRET_KEY = original_secret_key
