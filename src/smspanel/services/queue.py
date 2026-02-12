"""Task queue service for asynchronous SMS sending."""

import logging
import queue
import threading
from typing import Optional

from smspanel.models import Message, MessageJobStatus, RecipientStatus
from smspanel.utils.database import db_transaction
from smspanel.utils.rate_limiter import RateLimiter, get_rate_limiter


logger = logging.getLogger(__name__)

# Task function names that handle message sending
SMS_TASK_NAMES = frozenset({"process_single_sms_task", "process_bulk_sms_task"})


class TaskQueue:
    """In-memory task queue with background workers."""

    def __init__(self, num_workers: int = 4, max_queue_size: int = 1000):
        """Initialize the task queue.

        Args:
            num_workers: Number of background worker threads.
            max_queue_size: Maximum number of tasks to queue.
        """
        self.queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue_size)
        self.workers: list[threading.Thread] = []
        self.num_workers = num_workers
        self.running = False
        self.app = None
        self.rate_limiter: Optional[RateLimiter] = None
    def set_app(self, app):
        """Set the Flask app for app context.

        Args:
            app: Flask application instance.
        """
        self.app = app

    def enqueue(self, task_func, *args, priority: int = 1, **kwargs) -> bool:
        """Add a task to the queue.

        Args:
            task_func: Function to execute.
            *args: Positional arguments for task_func.
            priority: Priority level (0=highest, 1=normal, 2=low, etc.). Default is 1.
            **kwargs: Keyword arguments for task_func.

        Returns:
            True if task was enqueued, False if queue is full.
        """
        try:
            # PriorityQueue requires (priority, data) format
            self.queue.put((priority, (task_func, args, kwargs)), block=False)
            return True
        except queue.Full:
            logger.warning("Task queue is full, rejecting task")
            return False

    def _worker_loop(self, worker_id: int):
        """Main worker loop for processing tasks.

        Args:
            worker_id: Worker thread ID for logging.
        """
        from .dead_letter import get_dead_letter_queue

        logger.info(f"Worker {worker_id} started")
        while self.running:
            try:
                # PriorityQueue returns (priority, (task_func, args, kwargs))
                priority, (task_func, args, kwargs) = self.queue.get(timeout=1.0)
                # Check if this is an SMS task that needs job status tracking
                is_sms_task = (
                    hasattr(task_func, "__name__")
                    and task_func.__name__ in SMS_TASK_NAMES
                    and args
                    and isinstance(args[0], int)
                )
                message_id = args[0] if is_sms_task else None

                try:
                    # Acquire rate limiter token before processing
                    if self.rate_limiter is not None:
                        self.rate_limiter.acquire()
                    with self.app.app_context():
                        # Transition job_status to SENDING before processing
                        if is_sms_task:
                            self._update_message_job_status(message_id, MessageJobStatus.SENDING)
                        task_func(*args, **kwargs)
                        # Update final job status after task completes
                        if is_sms_task:
                            self._update_message_final_status(message_id)
                except Exception as e:
                    logger.error(f"Task execution error in worker {worker_id}: {e}", exc_info=True)
                    # Mark message as FAILED if it was an SMS task
                    if is_sms_task:
                        try:
                            self._update_message_final_status(message_id, MessageJobStatus.FAILED)
                        except Exception:
                            pass
                    # Try to capture to dead letter queue
                    try:
                        dlq = get_dead_letter_queue()
                        dlq.add(
                            message_id=message_id,
                            recipient=str(args) if args else "unknown",
                            content=str(kwargs) if kwargs else str(task_func),
                            error_message=str(e),
                            error_type=type(e).__name__,
                        )
                    except Exception as dlq_error:
                        logger.error(f"Failed to capture to dead letter queue: {dlq_error}")
                finally:
                    self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
        logger.info(f"Worker {worker_id} stopped")

    def _update_message_job_status(self, message_id: int, status: MessageJobStatus) -> None:
        """Update message job_status and clear queue_position.

        Args:
            message_id: Message ID to update.
            status: New job status value.
        """
        with db_transaction() as session:
            message = session.get(Message, message_id)
            if message:
                message.job_status = status
                message.queue_position = None

    def _update_message_final_status(
        self, message_id: int, default_status: MessageJobStatus = None
    ) -> None:
        """Update message job_status to final state based on recipient results.

        Args:
            message_id: Message ID to update.
            default_status: Status to use if message not found (e.g., FAILED on exception).
        """
        with db_transaction() as session:
            message = session.get(Message, message_id)
            if not message:
                return

            success_count = message.recipients.filter_by(status=RecipientStatus.SENT).count()
            failed_count = message.recipients.filter_by(status=RecipientStatus.FAILED).count()
            pending_count = message.recipients.filter_by(status=RecipientStatus.PENDING).count()

            if pending_count > 0:
                # Still pending recipients, keep SENDING status
                return

            total = success_count + failed_count
            if total == 0:
                # No recipients were processed, use default or keep current
                if default_status:
                    message.job_status = default_status
                return

            if success_count == total:
                message.job_status = MessageJobStatus.COMPLETED
            elif success_count > 0:
                message.job_status = MessageJobStatus.PARTIAL
            else:
                message.job_status = MessageJobStatus.FAILED

    def start(self):
        """Start the background workers."""
        if self.running:
            logger.warning("Task queue is already running")
            return

        self.running = True
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                name=f"SMSWorker-{i}",
                daemon=True,
            )
            worker.start()
            self.workers.append(worker)
        logger.info(f"Started {self.num_workers} background workers")

    def stop(self):
        """Stop the background workers."""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5.0)
        self.workers.clear()
        logger.info("Stopped background workers")

    def get_queue_size(self) -> int:
        """Get the current number of tasks in the queue.

        Returns:
            Number of pending tasks.
        """
        return self.queue.qsize()


# Global task queue instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get the global task queue instance.

    Returns:
        The global TaskQueue instance.

    Raises:
        RuntimeError: If task queue has not been initialized.
    """
    global _task_queue
    if _task_queue is None:
        raise RuntimeError("Task queue has not been initialized. Call init_task_queue() first.")
    return _task_queue


def init_task_queue(app, num_workers: int = 4, max_queue_size: int = 1000):
    """Initialize the task queue with Flask app context.

    Args:
        app: Flask application instance.
        num_workers: Number of background worker threads.
        max_queue_size: Maximum number of tasks to queue.
    """
    global _task_queue
    _task_queue = TaskQueue(num_workers=num_workers, max_queue_size=max_queue_size)
    _task_queue.set_app(app)

    # Set up rate limiter for workers
    _task_queue.rate_limiter = get_rate_limiter()

    # Start workers immediately
    _task_queue.start()

    # Clean up on shutdown
    @app.teardown_appcontext
    def shutdown_workers(exception=None):
        pass  # Workers are daemon threads, they'll be cleaned up on process exit
