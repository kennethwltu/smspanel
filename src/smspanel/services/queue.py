"""Task queue service for asynchronous SMS sending."""

import logging
import queue
import threading
from typing import Optional


logger = logging.getLogger(__name__)


class TaskQueue:
    """In-memory task queue with background workers."""

    def __init__(self, num_workers: int = 4, max_queue_size: int = 1000):
        """Initialize the task queue.

        Args:
            num_workers: Number of background worker threads.
            max_queue_size: Maximum number of tasks to queue.
        """
        self.queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.workers: list[threading.Thread] = []
        self.num_workers = num_workers
        self.running = False
        self.app = None

    def set_app(self, app):
        """Set the Flask app for app context.

        Args:
            app: Flask application instance.
        """
        self.app = app

    def enqueue(self, task_func, *args, **kwargs) -> bool:
        """Add a task to the queue.

        Args:
            task_func: Function to execute.
            *args: Positional arguments for task_func.
            **kwargs: Keyword arguments for task_func.

        Returns:
            True if task was enqueued, False if queue is full.
        """
        try:
            self.queue.put((task_func, args, kwargs), block=False)
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
                task_func, args, kwargs = self.queue.get(timeout=1.0)
                try:
                    with self.app.app_context():
                        task_func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Task execution error in worker {worker_id}: {e}", exc_info=True)
                    # Try to capture to dead letter queue
                    try:
                        dlq = get_dead_letter_queue()
                        dlq.add(
                            message_id=None,
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

    # Start workers immediately
    _task_queue.start()

    # Clean up on shutdown
    @app.teardown_appcontext
    def shutdown_workers(exception=None):
        pass  # Workers are daemon threads, they'll be cleaned up on process exit
