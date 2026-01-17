"""Admin routes for user management."""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from .. import db
from ..models import User

web_admin_bp = Blueprint("web_admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Decorator to require admin access."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("web.web_auth.login"))
        if not current_user.is_admin:
            flash("Admin access required.", "error")
            return redirect(url_for("web.web_sms.dashboard"))
        return f(*args, **kwargs)

    return decorated_function


@web_admin_bp.route("/users")
@login_required
@admin_required
def users():
    """List all users with actions."""
    # Sort by username ascending, admins at bottom
    users = User.query.order_by(User.is_admin.asc(), User.username.asc()).all()
    return render_template("admin/users.html", users=users)


@web_admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    """Create a new user."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        is_admin = request.form.get("is_admin") == "on"

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("admin/create_user.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("admin/create_user.html")

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return render_template("admin/create_user.html")

        user = User(username=username)
        user.set_password(password)
        user.token = User.generate_token()
        user.is_admin = is_admin
        user.is_active = True

        db.session.add(user)
        db.session.commit()

        flash(f"User '{username}' created successfully!", "success")
        return redirect(url_for("web.web_admin.users"))

    return render_template("admin/create_user.html")


@web_admin_bp.route("/users/<int:user_id>/password", methods=["GET", "POST"])
@login_required
@admin_required
def change_password(user_id):
    """Change user password."""
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("web.web_admin.users"))

    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not new_password:
            flash("New password is required.", "error")
            return render_template("admin/change_password.html", user=user)

        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("admin/change_password.html", user=user)

        user.set_password(new_password)
        db.session.commit()

        flash(f"Password for '{user.username}' changed successfully!", "success")
        return redirect(url_for("web.web_admin.users"))

    return render_template("admin/change_password.html", user=user)


@web_admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_active(user_id):
    """Toggle user active status (enable/disable)."""
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("web.web_admin.users"))

    # Prevent disabling self
    if user.id == current_user.id:
        flash("You cannot disable yourself.", "error")
        return redirect(url_for("web.web_admin.users"))

    user.is_active = not user.is_active
    status = "enabled" if user.is_active else "disabled"
    db.session.commit()

    flash(f"User '{user.username}' has been {status}.", "success")
    return redirect(url_for("web.web_admin.users"))


@web_admin_bp.route("/users/<int:user_id>/delete", methods=["GET", "POST"])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("web.web_admin.users"))

    # Prevent deleting self
    if user.id == current_user.id:
        flash("You cannot delete yourself.", "error")
        return redirect(url_for("web.web_admin.users"))

    if request.method == "POST":
        username = user.username
        db.session.delete(user)
        db.session.commit()

        flash(f"User '{username}' deleted successfully!", "success")
        return redirect(url_for("web.web_admin.users"))

    return render_template("admin/delete_user.html", user=user)


@web_admin_bp.route("/users/<int:user_id>/regenerate_token", methods=["POST"])
@login_required
@admin_required
def regenerate_token(user_id):
    """Regenerate the API token for a user."""
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("web.web_admin.users"))

    user.token = User.generate_token()
    db.session.commit()

    flash(f"API token regenerated for '{user.username}'.", "success")
    return redirect(url_for("web.web_admin.users"))
