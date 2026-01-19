"""Web UI SMS routes."""

import re
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from .. import db
from ..models import Message, Recipient
from ..services.hkt_sms import HKTSMSService

web_sms_bp = Blueprint("web_sms", __name__)

# Phone number regex: 4 digits, optional space, 4 digits (e.g., 1234 5678 or 12345678)
PHONE_REGEX = re.compile(r"^\d{4}\s?\d{4}$")
# Enquiry number regex: 4 digits, optional space, 4 digits
ENQUIRY_REGEX = re.compile(r"^\d{4}\s?\d{4}$")


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

    messages = (
        query.order_by(Message.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    total_messages = Message.query.filter_by(user_id=current_user.id).count()
    total_sent = Message.query.filter_by(user_id=current_user.id, status="sent").count()

    return render_template(
        "dashboard.html",
        messages=messages,
        total_messages=total_messages,
        total_sent=total_sent,
        time_filter=time_filter,
    )


@web_sms_bp.route("/compose", methods=["GET", "POST"])
@login_required
def compose():
    """Compose and send a new SMS message."""
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        recipients_input = request.form.get("recipients", "").strip()
        enquiry_number = request.form.get("enquiry_number", "").strip()

        # Enquiry number is mandatory and must match regex
        if not enquiry_number:
            flash("Enquiry Number is required.", "error")
            return render_template(
                "compose.html",
                content=content,
                recipients=recipients_input,
                enquiry_number=enquiry_number,
            )

        if not ENQUIRY_REGEX.match(enquiry_number):
            flash(
                "Invalid Enquiry Number format. Must be in format: 4 digits, optional space, 4 digits (e.g., 1234 5678 or 12345678).",
                "error",
            )
            return render_template(
                "compose.html",
                content=content,
                recipients=recipients_input,
                enquiry_number=enquiry_number,
            )

        # Message field is mandatory
        if not content:
            flash("Message content is required.", "error")
            return render_template(
                "compose.html",
                content=content,
                recipients=recipients_input,
                enquiry_number=enquiry_number,
            )

        # Parse recipients (one per row, ignore empty lines)
        recipients = [r.strip() for r in recipients_input.split("\n") if r.strip()]

        # Recipients must have at least one number
        if not recipients:
            flash("At least one recipient is required.", "error")
            return render_template(
                "compose.html",
                content=content,
                recipients=recipients_input,
                enquiry_number=enquiry_number,
            )

        # Validate each phone number matches regex \d{4}\s?\d{4}
        invalid_numbers = []
        valid_recipients = []
        for r in recipients:
            if not PHONE_REGEX.match(r):
                invalid_numbers.append(r)
            else:
                valid_recipients.append(r)

        if invalid_numbers:
            flash(
                f"Invalid phone number format: {', '.join(invalid_numbers)}. "
                "Each number must be in format: 4 digits, optional space, 4 digits (e.g., 1234 5678 or 12345678).",
                "error",
            )
            return render_template(
                "compose.html",
                content=content,
                recipients=recipients_input,
                enquiry_number=enquiry_number,
            )

        recipients = valid_recipients

        # Append enquiry number to message content
        sms_content = f"{content} EN:{enquiry_number}"

        # Create message record
        message = Message(user_id=current_user.id, content=sms_content, status="pending")
        db.session.add(message)
        db.session.flush()

        # Create recipient records
        for recipient in recipients:
            recipient_record = Recipient(message_id=message.id, phone=recipient, status="pending")
            db.session.add(recipient_record)

        db.session.commit()

        # Send SMS via HKT
        sms_service = HKTSMSService()
        result = sms_service.send_bulk(recipients, sms_content)

        # Update records based on result
        all_sent = result["success"]
        message.status = "sent" if all_sent else "partial" if result["successful"] > 0 else "failed"
        if all_sent:
            message.sent_at = datetime.now(timezone.utc)

        # Update individual recipient statuses
        for i, recipient_result in enumerate(result["results"]):
            recipient_record = message.recipients[i]
            if recipient_result["success"]:
                recipient_record.status = "sent"
            else:
                recipient_record.status = "failed"
                recipient_record.error_message = recipient_result.get("error", "Unknown error")

        db.session.commit()

        if all_sent:
            flash(f"Successfully sent {result['total']} message(s).", "success")
        elif result["successful"] > 0:
            flash(
                f"Partially sent: {result['successful']} successful, {result['failed']} failed.",
                "warning",
            )
        else:
            flash("Failed to send messages. Please try again.", "error")

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

    messages = (
        query.order_by(Message.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
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
