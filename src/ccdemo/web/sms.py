"""Web UI SMS routes."""

from datetime import datetime
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from .. import db
from ..models import Message, Recipient
from ..services.hkt_sms import HKTSMSService

web_sms_bp = Blueprint("web_sms", __name__)


@web_sms_bp.route("/")
@login_required
def dashboard():
    """Dashboard with recent messages and quick send."""
    recent_messages = (
        Message.query.filter_by(user_id=current_user.id)
        .order_by(Message.created_at.desc())
        .limit(10)
        .all()
    )

    total_messages = Message.query.filter_by(user_id=current_user.id).count()
    total_sent = Message.query.filter_by(user_id=current_user.id, status="sent").count()

    return render_template(
        "dashboard.html",
        messages=recent_messages,
        total_messages=total_messages,
        total_sent=total_sent,
    )


@web_sms_bp.route("/compose", methods=["GET", "POST"])
@login_required
def compose():
    """Compose and send a new SMS message."""
    if request.method == "POST":
        content = request.form.get("content")
        recipients_input = request.form.get("recipients")

        if not content or not recipients_input:
            flash("Message content and recipients are required.", "error")
            return render_template("compose.html", content=content, recipients=recipients_input)

        # Parse recipients (comma or newline separated)
        recipients = [r.strip() for r in recipients_input.replace("\n", ",").split(",") if r.strip()]

        if not recipients:
            flash("At least one recipient is required.", "error")
            return render_template("compose.html", content=content, recipients=recipients_input)

        # Create message record
        message = Message(user_id=current_user.id, content=content, status="pending")
        db.session.add(message)
        db.session.flush()

        # Create recipient records
        for recipient in recipients:
            recipient_record = Recipient(message_id=message.id, phone=recipient, status="pending")
            db.session.add(recipient_record)

        db.session.commit()

        # Send SMS via HKT
        sms_service = HKTSMSService()
        result = sms_service.send_bulk(recipients, content)

        # Update records based on result
        all_sent = result["success"]
        message.status = "sent" if all_sent else "partial" if result["successful"] > 0 else "failed"
        if all_sent:
            message.sent_at = datetime.utcnow()

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
            flash(f"Partially sent: {result['successful']} successful, {result['failed']} failed.", "warning")
        else:
            flash("Failed to send messages. Please try again.", "error")

        return redirect(url_for("web.sms_detail", message_id=message.id))

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

    messages = query.order_by(Message.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

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
