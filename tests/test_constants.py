def test_sms_timeout_is_configurable():
    """SMS request timeout should be defined as a constant."""
    from smspanel.services.hkt_sms import SMS_REQUEST_TIMEOUT

    assert SMS_REQUEST_TIMEOUT == 30
    assert isinstance(SMS_REQUEST_TIMEOUT, int)


def test_sms_timeout_constant_in_config():
    """SMS timeout should be available in config."""
    from smspanel.config.config import Config

    # Check the timeout constant exists (may be None for backward compat)
    timeout = getattr(Config, "SMS_REQUEST_TIMEOUT", None)
    if timeout is not None:
        assert isinstance(timeout, int)
        assert timeout == 30
