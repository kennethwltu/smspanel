"""Admin routes for message management and querying."""

from datetime import datetime
from flask import Blueprint, request, render_template
from flask_login import login_required, current_user
from werkzeug.wrappers import Response

from smspanel.models import User, Message

web_admin_messages_bp = Blueprint("web_admin_messages", __name__, url_prefix="/admin/messages")


@web_admin_messages_bp.route("")
@login_required
def messages():
    """List messages with filters for admin."""
    if not current_user.is_admin:
        return Response("Forbidden", status=403)

    # Filters
    user_id = request.args.get("user_id", type=int)
    status = request.args.get("status")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    page = request.args.get("page", 1, type=int)
    per_page = 50

    # Build query
    query = Message.query

    if user_id:
        query = query.filter_by(user_id=user_id)

    if status:
        query = query.filter_by(status=status)

    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.filter(Message.created_at >= start_dt)

    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.filter(Message.created_at <= end_dt)

    # Get total count before pagination
    total_count = query.count()

    # Paginate
    messages = query.order_by(Message.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get users for filter dropdown
    users = User.query.order_by(User.username.asc()).all()

    return render_template(
        "admin/messages.html",
        messages=messages,
        users=users,
        total_count=total_count,
        user_id=user_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
