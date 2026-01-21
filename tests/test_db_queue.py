from smspanel import db


def test_db_queue_exists():
    """Database-backed queue should exist."""
    from smspanel.services.db_queue import DatabaseQueue

    assert DatabaseQueue is not None


def test_db_queue_persists_tasks(app):
    """Database queue should persist tasks in database."""
    from smspanel.services.db_queue import DatabaseQueue, QueuedTask

    with app.app_context():
        db.create_all()
        q = DatabaseQueue()
        q.enqueue("test_task", "arg1", kwarg1="value1")

        # Task should be in database
        count = QueuedTask.query.count()
        assert count == 1
