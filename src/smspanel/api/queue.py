"""Queue status API endpoints."""

from flask import Blueprint

from smspanel.models import Message, MessageJobStatus
from smspanel.services.queue import get_task_queue
from smspanel.utils.rate_limiter import get_rate_limiter
from smspanel.extensions import db
from smspanel.api.responses import APIResponse

api_queue_bp = Blueprint("api_queue", __name__)


@api_queue_bp.route("/queue/status", methods=["GET"])
def queue_status() -> tuple:
    """Get current queue status and statistics.

    Returns:
        JSON with queue depth, rate limit info, and per-user stats if authenticated.
    """
    queue = get_task_queue()
    limiter = get_rate_limiter()

    # Count pending messages in queue (job_status = PENDING)
    pending_count = (
        db.session.query(Message).filter(Message.job_status == MessageJobStatus.PENDING).count()
    )

    # Count sending messages
    sending_count = (
        db.session.query(Message).filter(Message.job_status == MessageJobStatus.SENDING).count()
    )

    # Get oldest pending message for estimating wait time
    oldest = (
        db.session.query(Message)
        .filter(Message.job_status == MessageJobStatus.PENDING)
        .order_by(Message.created_at.asc())
        .first()
    )

    data = {
        "queue_depth": queue.get_queue_size(),
        "msgs_per_sec": limiter.rate_per_sec,
        "pending_messages": pending_count,
        "sending_messages": sending_count,
        "oldest_pending_at": oldest.created_at.isoformat() if oldest else None,
    }

    return APIResponse.success(data=data)
