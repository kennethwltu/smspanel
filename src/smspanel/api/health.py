"""Health check endpoint for monitoring and load balancers."""

from flask import Blueprint, jsonify
from datetime import datetime, timezone
import os

from smspanel import db


api_health_bp = Blueprint("api_health", __name__)


@api_health_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring.

    Returns:
        JSON response with health status and system information.
    """
    checks = {
        "database": _check_database(),
        "memory": _check_memory(),
    }

    # Determine overall status
    all_healthy = all(check["healthy"] for check in checks.values())
    overall_status = "healthy" if all_healthy else "unhealthy"

    response_data = {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": _get_version(),
        "checks": checks,
    }

    status_code = 200 if all_healthy else 503

    return jsonify(response_data), status_code


@api_health_bp.route("/health/live", methods=["GET"])
def liveness():
    """Simple liveness probe.

    Returns:
        JSON response indicating if the app is alive.
    """
    return jsonify({"status": "alive"}), 200


@api_health_bp.route("/health/ready", methods=["GET"])
def readiness():
    """Readiness probe (includes database check).

    Returns:
        JSON response indicating if the app is ready.
    """
    db_healthy = _check_database()["healthy"]

    if db_healthy:
        return jsonify({"status": "ready"}), 200
    else:
        return jsonify({"status": "not ready", "reason": "Database not connected"}), 503


def _check_database() -> dict:
    """Check database connectivity.

    Returns:
        Health check result dictionary.
    """
    try:
        # Execute a simple query
        db.session.execute(db.text("SELECT 1"))
        return {"healthy": True, "message": "Connected"}
    except Exception as e:
        return {"healthy": False, "message": str(e)}


def _check_memory() -> dict:
    """Check memory usage.

    Returns:
        Health check result dictionary.
    """
    try:
        import psutil

        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        memory_mb = mem_info.rss / (1024 * 1024)

        return {
            "healthy": memory_mb < 500,  # Less than 500MB
            "message": f"{memory_mb:.1f} MB used",
            "used_mb": round(memory_mb, 1),
        }
    except ImportError:
        # psutil not installed, skip memory check
        return {"healthy": True, "message": "psutil not installed", "skipped": True}
    except Exception as e:
        return {"healthy": False, "message": str(e)}


def _get_version() -> str:
    """Get application version.

    Returns:
        Version string.
    """
    try:
        from smspanel.config import config as config_dict

        env = getattr(config_dict, "FLASK_ENV", "unknown")
        return f"smspanel-{env}"
    except Exception:
        return "smspanel-unknown"
