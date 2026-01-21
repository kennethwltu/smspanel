def test_dead_letter_message_exported():
    """DeadLetterMessage should be exported from models."""
    from smspanel.models import DeadLetterMessage

    assert DeadLetterMessage is not None
