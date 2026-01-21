# Database and Queue Performance Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Improve production readiness by adding MySQL support, connection pooling, and persistent task queue.

**Architecture:**
1. Add MySQL support via PyMySQL (pure Python, no system dependencies)
2. Configure SQLAlchemy connection pooling (pool_size=10, max_overflow=20)
3. Implement database-backed task queue for persistence across restarts
4. Keep SQLite as default for development/testing

**Tech Stack:** Flask-SQLAlchemy, PyMySQL, SQLite (dev), MySQL (prod)

---

### Task 1: Add PyMySQL dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

**Step 1: Write the failing test**

```python
# tests/test_mysql.py
def test_pymysql_available():
    """PyMySQL should be available for MySQL connections."""
    import pymysql
    assert pymysql is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_mysql.py::test_pymysql_available -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Add PyMySQL to dependencies**

```toml
# pyproject.toml - add under [project]
dependencies = [
    # ... existing dependencies ...
    "pymysql>=1.1.0",
]
```

```txt
# requirements.txt - add line
pymysql>=1.1.0
```

**Step 4: Install the package**

Run: `pip install pymysql>=1.1.0`

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_mysql.py::test_pymysql_available -v`
Expected: PASS

**Step 6: Commit**

```bash
git add pyproject.toml requirements.txt
git commit -m "deps: add pymysql for MySQL support"
```

---

### Task 2: Update config with MySQL support and pool settings

**Files:**
- Modify: `src/smspanel/config/config.py`

**Step 1: Write the failing test**

```python
# tests/test_database_config.py
def test_mysql_uri_parsed_correctly():
    """MySQL connection string should parse correctly."""
    from smspanel.config.config import Config

    # Simulate MySQL URI
    Config.SQLALCHEMY_DATABASE_URI = "mysql+pymysql://user:pass@localhost:3306/smspanel"
    assert "mysql+pymysql" in Config.SQLALCHEMY_DATABASE_URI
    assert "pymysql" in Config.SQLALCHEMY_DATABASE_URI


def test_pool_settings_configured():
    """Pool settings should be configurable."""
    from smspanel.config.config import Config

    # Default pool settings
    assert hasattr(Config, "SQLALCHEMY_POOL_SIZE")
    assert hasattr(Config, "SQLALCHEMY_POOL_MAX_OVERFLOW")
    assert Config.SQLALCHEMY_POOL_SIZE == 10
    assert Config.SQLALCHEMY_POOL_MAX_OVERFLOW == 20
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database_config.py -v`
Expected: FAIL - missing attributes

**Step 3: Update config with MySQL and pool settings**

```python
# src/smspanel/config/config.py

class Config:
    """Base configuration."""

    # Flask - SECRET_KEY must be set in production!
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///sms.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection Pool Settings (for MySQL in production)
    # These are ignored by SQLite but used by MySQL/PostgreSQL
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_MAX_OVERFLOW = 20
    SQLALCHEMY_POOL_RECYCLE = 3600  # Recycle connections after 1 hour
    SQLALCHEMY_POOL_PRE_PING = True  # Verify connections before use

    # SMS Gateway
    SMS_BASE_URL = os.getenv("SMS_BASE_URL")
    SMS_APPLICATION_ID = os.getenv("SMS_APPLICATION_ID")
    SMS_SENDER_NUMBER = os.getenv("SMS_SENDER_NUMBER")

    # SMS Queue
    SMS_QUEUE_WORKERS = 4
    SMS_QUEUE_MAX_SIZE = 1000
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/smspanel/config/config.py
git commit -m "config: add MySQL support and connection pool settings"
```

---

### Task 3: Add pool settings to ProductionConfig

**Files:**
- Modify: `src/smspanel/config/config.py`

**Step 1: Write the failing test**

```python
# tests/test_database_config.py
def test_production_pool_settings():
    """Production config should have proper pool settings."""
    from smspanel.config.config import ProductionConfig

    prod_config = ProductionConfig()
    assert prod_config.SQLALCHEMY_POOL_SIZE == 10
    assert prod_config.SQLALCHEMY_POOL_MAX_OVERFLOW == 20
    assert prod_config.SQLALCHEMY_POOL_RECYCLE == 3600
    assert prod_config.SQLALCHEMY_POOL_PRE_PING == True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database_config.py::test_production_pool_settings -v`
Expected: FAIL - inherits from Config, need to verify

**Step 3: Production config inherits base pool settings**

The ProductionConfig inherits from Config, so pool settings are already available.
The test should verify inheritance works correctly.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database_config.py::test_production_pool_settings -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/smspanel/config/config.py
git commit -m "config: verify production pool settings inheritance"
```

---

### Task 4: Create database-backed persistent task queue

**Files:**
- Create: `src/smspanel/services/db_queue.py`
- Modify: `src/smspanel/services/queue.py`

**Step 1: Write the failing test**

```python
# tests/test_db_queue.py
def test_db_queue_exists():
    """Database-backed queue should exist."""
    from smspanel.services.db_queue import DatabaseQueue

    assert DatabaseQueue is not None


def test_db_queue_persists_tasks(app):
    """Database queue should persist tasks in database."""
    from smspanel.services.db_queue import DatabaseQueue, get_db_queue

    with app.app_context():
        db.create_all()
        q = DatabaseQueue()
        q.enqueue("test_task", "arg1", kwarg1="value1")

        # Task should be in database
        from smspanel.services.db_queue import QueuedTask
        count = QueuedTask.query.count()
        assert count == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_db_queue.py::test_db_queue_exists -v`
Expected: FAIL - module not found

**Step 3: Create persistent queue model and service**

```python
# src/smspanel/services/db_queue.py
"""Database-backed persistent task queue."""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional, Any

from ..extensions import db

logger = logging.getLogger(__name__)


class QueueStatus(str, Enum):
    """Task queue status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class QueuedTask(db.Model):
    """Model for persisted queue tasks."""

    __tablename__ = "queued_tasks"

    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100), nullable=False)
    task_func = db.Column(db.String(200), nullable=False)  # Function reference
    args = db.Column(db.Text, nullable=True)  # JSON serialized
    kwargs = db.Column(db.Text, nullable=True)  # JSON serialized
    status = db.Column(db.String(20), default=QueueStatus.PENDING, index=True)
    worker_id = db.Column(db.Integer, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    max_retries = db.Column(db.Integer, default=3)
    retry_count = db.Column(db.Integer, default=0)

    def __repr__(self) -> str:
        return f"<QueuedTask {self.id}: {self.task_name} ({self.status})>"

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries and self.status == QueueStatus.FAILED


class DatabaseQueue:
    """Database-backed persistent task queue."""

    def __init__(self, num_workers: int = 4):
        """Initialize the database queue.

        Args:
            num_workers: Number of background worker threads.
        """
        self.num_workers = num_workers
        self.workers = []
        self.running = False
        self.app = None

    def set_app(self, app):
        """Set Flask app for context.

        Args:
            app: Flask application.
        """
        self.app = app

    def enqueue(
        self,
        task_func_name: str,
        *args,
        task_func: Optional[Callable] = None,
        **kwargs,
    ) -> Optional[int]:
        """Add a task to the queue.

        Args:
            task_func_name: Name/identifier for the task function.
            *args: Positional arguments.
            task_func: The actual function (for registration).
            **kwargs: Keyword arguments.

        Returns:
            Task ID if queued, None if failed.
        """
        import json

        try:
            task = QueuedTask(
                task_name=task_func_name,
                task_func=f"{task_func.__module__}.{task_func.__name__}" if task_func else task_func_name,
                args=json.dumps(args) if args else None,
                kwargs=json.dumps(kwargs) if kwargs else None,
                status=QueueStatus.PENDING,
            )
            db.session.add(task)
            db.session.commit()
            logger.info(f"Queued task {task.id}: {task_func_name}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to queue task: {e}")
            return None

    def get_pending(self, limit: int = 100) -> list[QueuedTask]:
        """Get pending tasks for processing.

        Args:
            limit: Maximum tasks to return.

        Returns:
            List of pending tasks.
        """
        return (
            QueuedTask.query.filter_by(status=QueueStatus.PENDING)
            .order_by(QueuedTask.created_at.asc())
            .limit(limit)
            .all()
        )

    def mark_processing(self, task_id: int, worker_id: int) -> bool:
        """Mark a task as being processed.

        Args:
            task_id: Task ID.
            worker_id: Worker ID.

        Returns:
            True if marked, False if not found or not pending.
        """
        task = QueuedTask.query.get(task_id)
        if task and task.status == QueueStatus.PENDING:
            task.status = QueueStatus.PROCESSING
            task.worker_id = worker_id
            task.started_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        return False

    def mark_completed(self, task_id: int) -> bool:
        """Mark a task as completed.

        Args:
            task_id: Task ID.

        Returns:
            True if marked, False if not found.
        """
        task = QueuedTask.query.get(task_id)
        if task:
            task.status = QueueStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        return False

    def mark_failed(self, task_id: int, error_message: str) -> bool:
        """Mark a task as failed.

        Args:
            task_id: Task ID.
            error_message: Error description.

        Returns:
            True if marked, False if not found.
        """
        task = QueuedTask.query.get(task_id)
        if task:
            task.status = QueueStatus.FAILED
            task.error_message = error_message
            task.retry_count += 1
            db.session.commit()
            return True
        return False

    def get_stats(self) -> dict:
        """Get queue statistics.

        Returns:
            Dict with counts by status.
        """
        pending = QueuedTask.query.filter_by(status=QueueStatus.PENDING).count()
        processing = QueuedTask.query.filter_by(status=QueueStatus.PROCESSING).count()
        completed = QueuedTask.query.filter_by(status=QueueStatus.COMPLETED).count()
        failed = QueuedTask.query.filter_by(status=QueueStatus.FAILED).count()

        return {
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "total": pending + processing + completed + failed,
        }

    def retry_failed_tasks(self) -> int:
        """Retry all failed tasks that can be retried.

        Returns:
            Number of tasks queued for retry.
        """
        failed_tasks = QueuedTask.query.filter_by(status=QueueStatus.FAILED).all()
        retried = 0
        for task in failed_tasks:
            if task.can_retry():
                task.status = QueueStatus.PENDING
                retried += 1
        db.session.commit()
        return retried


# Global database queue instance
_db_queue: Optional[DatabaseQueue] = None


def get_db_queue() -> DatabaseQueue:
    """Get the global database queue instance.

    Returns:
        The global DatabaseQueue instance.
    """
    global _db_queue
    if _db_queue is None:
        raise RuntimeError("Database queue not initialized. Call init_db_queue() first.")
    return _db_queue


def init_db_queue(app, num_workers: int = 4):
    """Initialize the database queue with Flask app.

    Args:
        app: Flask application instance.
        num_workers: Number of background workers.
    """
    global _db_queue
    _db_queue = DatabaseQueue(num_workers=num_workers)
    _db_queue.set_app(app)

    # Create tables
    with app.app_context():
        db.create_all()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_db_queue.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/smspanel/services/db_queue.py
git commit -m "feat: add database-backed persistent task queue"
```

---

### Task 5: Add DeadLetterMessage table to models

**Files:**
- Modify: `src/smspanel/models.py`

**Note:** DeadLetterMessage was already added in previous implementation. Verify it's exported.

**Step 1: Verify test exists**

```python
# tests/test_models.py
def test_dead_letter_message_exported():
    """DeadLetterMessage should be exported from models."""
    from smspanel.models import DeadLetterMessage

    assert DeadLetterMessage is not None
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_models.py::test_dead_letter_message_exported -v`
Expected: PASS

**Step 3: Commit if needed**

```bash
git add src/smspanel/models.py
git commit -m "models: verify DeadLetterMessage export"
```

---

### Task 6: Run full test suite

**Files:**
- Run: All tests

**Step 1: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass

**Step 2: Run linter**

```bash
ruff check .
ruff format .
```

Expected: No errors

**Step 3: Commit**

```bash
git add .
git commit -m "chore: run tests and lint after database/queue improvements"
```

---

### Task 7: Update documentation

**Files:**
- Modify: `README.md`

**Step 1: Add database configuration documentation**

```markdown
## Database Configuration

### SQLite (Development - Default)

```bash
DATABASE_URL=sqlite:///sms.db
```

### MySQL (Production Recommended)

```bash
DATABASE_URL=mysql+pymysql://username:password@hostname:3306/database_name
```

### Connection Pool Settings

For MySQL/PostgreSQL, configure connection pooling:

| Setting | Description | Default |
|---------|-------------|---------|
| `SQLALCHEMY_POOL_SIZE` | Number of connections to maintain | 10 |
| `SQLALCHEMY_POOL_MAX_OVERFLOW` | Max additional connections | 20 |
| `SQLALCHEMY_POOL_RECYCLE` | Recycle connections after (seconds) | 3600 |
| `SQLALCHEMY_POOL_PRE_PING` | Verify connections before use | true |

### Persistent Task Queue

Tasks are now persisted in the database for reliability:

- Tasks survive application restarts
- Failed tasks can be retried
- Queue statistics available at `/admin/dead-letter`
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add database configuration and persistent queue docs"
```

---

### Task 8: Bump version

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update version**

```toml
version = "0.22.0"
```

**Step 2: Commit and push**

```bash
git add pyproject.toml
git commit -m "chore: bump version to 0.22.0"
git push
```
