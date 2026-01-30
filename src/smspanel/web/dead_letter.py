"""Admin routes for dead letter queue management."""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from smspanel.services.dead_letter import get_dead_letter_queue
from smspanel.constants.messages import (
    AUTH_ADMIN_REQUIRED,
    AUTH_LOGIN_REQUIRED,
)

web_dead_letter_bp = Blueprint("web_dead_letter", __name__, url_prefix="/admin/dead-letter")


def admin_required(f):
    """Decorator to require admin access."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash(AUTH_LOGIN_REQUIRED, "error")
            return redirect(url_for("web.web_auth.login"))
        if not current_user.is_admin:
            flash(AUTH_ADMIN_REQUIRED, "error")
            return redirect(url_for("web.web_sms.dashboard"))
        return f(*args, **kwargs)

    return decorated_function


@web_dead_letter_bp.route("")
@login_required
@admin_required
def list_dead_letter():
    """List all dead letter messages."""
    status = request.args.get("status")
    dlq = get_dead_letter_queue()
    stats = dlq.get_stats()

    messages = dlq.get_all(status=status, limit=100)

    return render_template(
        "admin/dead_letter.html",
        messages=messages,
        stats=stats,
        current_status=status,
    )


@web_dead_letter_bp.route("/retry/<int:message_id>", methods=["POST"])
@login_required
@admin_required
def retry_dead_letter(message_id: int):
    """Retry a dead letter message."""
    dlq = get_dead_letter_queue()

    if dlq.retry(message_id):
        flash(f"Dead letter {message_id} queued for retry.", "success")
    else:
        flash(f"Dead letter {message_id} cannot be retried (max retries exceeded).", "error")

    return redirect(url_for("web.web_dead_letter.list_dead_letter"))


@web_dead_letter_bp.route("/abandon/<int:message_id>", methods=["POST"])
@login_required
@admin_required
def abandon_dead_letter(message_id: int):
    """Mark a dead letter message as abandoned."""
    dlq = get_dead_letter_queue()

    if dlq.mark_abandoned(message_id):
        flash(f"Dead letter {message_id} marked as abandoned.", "info")
    else:
        flash(f"Dead letter {message_id} not found.", "error")

    return redirect(url_for("web.web_dead_letter.list_dead_letter"))


@web_dead_letter_bp.route("/retry-all", methods=["POST"])
@login_required
@admin_required
def retry_all_dead_letter():
    """Retry all pending dead letter messages."""
    dlq = get_dead_letter_queue()
    messages = dlq.get_pending()

    retry_count = 0
    for msg in messages:
        if dlq.retry(msg.id):
            retry_count += 1

    flash(f"{retry_count} dead letter messages queued for retry.", "success")
    return redirect(url_for("web.web_dead_letter.list_dead_letter"))
