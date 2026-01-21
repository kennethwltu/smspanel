"""Tests for database indexes."""


def test_message_compound_index_exists():
    """Message table should have compound index on (user_id, created_at)."""
    from smspanel.models import Message

    # Get the actual table
    table = Message.__table__

    # Check for compound index with both user_id and created_at
    has_compound_idx = any(
        "ix_messages_user_id_created_at" == idx.name
        or (
            hasattr(idx, "columns")
            and set(["user_id", "created_at"]).issubset({c.name for c in idx.columns})
        )
        for idx in table.indexes
    )

    assert has_compound_idx, "Compound index on (user_id, created_at) should exist"
