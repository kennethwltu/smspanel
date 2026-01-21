"""Database-backed persistent task queue."""

import logging
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional

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
    task_func = db.Column(db.String(200), nullable=False)
    args = db.Column(db.Text, nullable=True)
    kwargs = db.Column(db.Text, nullable=True)
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
        self.num_workers = num_workers
        self.workers = []
        self.running = False
        self.app = None

    def set_app(self, app):
        self.app = app

    def enqueue(
        self,
        task_func_name: str,
        *args,
        task_func: Optional[Callable] = None,
        **kwargs,
    ) -> Optional[int]:
        """Add a task to the queue."""
        try:
            task = QueuedTask(
                task_name=task_func_name,
                task_func=f"{task_func.__module__}.{task_func.__name__}"
                if task_func
                else task_func_name,
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
        """Get pending tasks for processing."""
        return (
            QueuedTask.query.filter_by(status=QueueStatus.PENDING)
            .order_by(QueuedTask.created_at.asc())
            .limit(limit)
            .all()
        )

    def mark_processing(self, task_id: int, worker_id: int) -> bool:
        """Mark a task as being processed."""
        task = QueuedTask.query.get(task_id)
        if task and task.status == QueueStatus.PENDING:
            task.status = QueueStatus.PROCESSING
            task.worker_id = worker_id
            task.started_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        return False

    def mark_completed(self, task_id: int) -> bool:
        """Mark a task as completed."""
        task = QueuedTask.query.get(task_id)
        if task:
            task.status = QueueStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        return False

    def mark_failed(self, task_id: int, error_message: str) -> bool:
        """Mark a task as failed."""
        task = QueuedTask.query.get(task_id)
        if task:
            task.status = QueueStatus.FAILED
            task.error_message = error_message
            task.retry_count += 1
            db.session.commit()
            return True
        return False

    def get_stats(self) -> dict:
        """Get queue statistics."""
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
        """Retry all failed tasks that can be retried."""
        failed_tasks = QueuedTask.query.filter_by(status=QueueStatus.FAILED).all()
        retried = 0
        for task in failed_tasks:
            if task.can_retry():
                task.status = QueueStatus.PENDING
                retried += 1
        db.session.commit()
        return retried


_db_queue: Optional[DatabaseQueue] = None


def get_db_queue() -> DatabaseQueue:
    """Get the global database queue instance."""
    global _db_queue
    if _db_queue is None:
        raise RuntimeError("Database queue not initialized. Call init_db_queue() first.")
    return _db_queue


def init_db_queue(app, num_workers: int = 4):
    """Initialize the database queue with Flask app."""
    global _db_queue
    _db_queue = DatabaseQueue(num_workers=num_workers)
    _db_queue.set_app(app)

    with app.app_context():
        db.create_all()
