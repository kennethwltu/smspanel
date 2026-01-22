"""Web UI SMS routes."""

from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from smspanel.models import Message, MessageJobStatus
from smspanel.services.queue import get_task_queue
from smspanel.utils.rate_limiter import get_rate_limiter
from smspanel.utils.validation import (
    validate_enquiry_number,
    validate_message_content,
    validate_recipients,
    format_phone_error,
)
from smspanel.utils.sms_helper import (
    create_message_record,
    create_recipient_records,
    update_message_status_from_result,
    get_flash_message_from_result,
)
from smspanel.utils.database import db_transaction

web_sms_bp = Blueprint("web_sms", __name__)


@web_sms_bp.route("/")
@login_required
def dashboard():
    """Dashboard with messages filtered by time period."""
    time_filter = request.args.get("time_filter", "today")
    per_page = 20
    page = request.args.get("page", 1, type=int)

    # Calculate time range based on filter
    now = datetime.now(timezone.utc)
    if time_filter == "3h":
        start_time = now - timedelta(hours=3)
    elif time_filter == "7d":
        start_time = now - timedelta(days=7)
    else:  # today
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Build query with time filter
    query = Message.query.filter_by(user_id=current_user.id).filter(
        Message.created_at >= start_time
    )

    messages = query.order_by(Message.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    total_messages = Message.query.filter_by(user_id=current_user.id).count()
    total_sent = Message.query.filter_by(user_id=current_user.id, status="sent").count()

    # Get queue status
    queue = get_task_queue()
    limiter = get_rate_limiter()

    # Get user's pending messages
    user_pending = Message.query.filter_by(
        user_id=current_user.id,
        job_status=MessageJobStatus.PENDING
    ).count()

    queue_status = {
        "depth": queue.get_queue_size(),
        "rate": limiter.rate_per_sec,
        "user_pending": user_pending,
    }

    return render_template(
        "dashboard.html",
        messages=messages,
        total_messages=total_messages,
        total_sent=total_sent,
        time_filter=time_filter,
        queue_status=queue_status,
    )


@web_sms_bp.route("/compose", methods=["GET", "POST"])
@login_required
def compose():
    """Compose and send a new SMS message."""
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        recipients_input = request.form.get("recipients", "").strip()
        enquiry_number = request.form.get("enquiry_number", "").strip()

        # Validate enquiry number
        is_valid, error_msg = validate_enquiry_number(enquiry_number)
        if not is_valid:
            flash(error_msg, "error")
            return render_template(
                "compose.html",
                content=content,
                recipients=recipients_input,
                enquiry_number=enquiry_number,
            )

        # Validate message content
        is_valid, error_msg = validate_message_content(content)
        if not is_valid:
            flash(error_msg, "error")
            return render_template(
                "compose.html",
                content=content,
                recipients=recipients_input,
                enquiry_number=enquiry_number,
            )

        # Validate recipients
        valid_recipients, invalid_numbers = validate_recipients(recipients_input)

        if not valid_recipients:
            flash("At least one recipient is required.", "error")
            return render_template(
                "compose.html",
                content=content,
                recipients=recipients_input,
                enquiry_number=enquiry_number,
            )

        if invalid_numbers:
            flash(format_phone_error(invalid_numbers), "error")
            return render_template(
                "compose.html",
                content=content,
                recipients=recipients_input,
                enquiry_number=enquiry_number,
            )

        # Append enquiry number to message content
        sms_content = f"{content} EN:{enquiry_number}"

        # Create message and recipient records
        with db_transaction() as session:
            message = create_message_record(current_user.id, sms_content)
            create_recipient_records(message.id, valid_recipients)

        # Send SMS via SMS gateway
        from smspanel.utils.sms_helper import get_sms_service

        sms_service = get_sms_service()
        result = sms_service.send_bulk(valid_recipients, sms_content)

        # Update message status based on result
        with db_transaction() as session:
            session.add(message)
            update_message_status_from_result(message, result)

        # Flash appropriate message
        flash_type, flash_msg = get_flash_message_from_result(result)
        flash(flash_msg, flash_type)

        return redirect(url_for("web.web_sms.sms_detail", message_id=message.id))

    return render_template("compose.html")


@web_sms_bp.route("/history")
@login_required
def history():
    """Message history with search and filter."""
    page = request.args.get("page", 1, type=int)
    per_page = 20
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Message.query.filter_by(user_id=current_user.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search:
        query = query.filter(Message.content.ilike(f"%{search}%"))

    messages = query.order_by(Message.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        "history.html",
        messages=messages,
        search=search,
        status_filter=status_filter,
    )


@web_sms_bp.route("/history/<int:message_id>")
@login_required
def sms_detail(message_id: int):
    """View details of a specific message."""
    message = Message.query.filter_by(id=message_id, user_id=current_user.id).first_or_404()
    recipients = message.recipients.all()

    return render_template("sms_detail.html", message=message, recipients=recipients)
