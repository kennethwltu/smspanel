# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

Standard Python package layout:

- `src/smspanel/` - Main source code (installable package)
- `tests/` - Pytest tests
- `scripts/` - Utility scripts (mock SMS API)
- `pyproject.toml` - Project configuration, pytest settings, ruff config

## Architecture Overview

### Application Factory Pattern

The app uses Flask's application factory pattern in `app.py`. `create_app()` returns a configured Flask instance and handles:
1. Configuration loading (Dev/Prod/Test environments via `config/config.py`)
2. Extension initialization (`db`, `login_manager`)
3. Blueprint registration (API under `/api/*`, Web routes without prefix)
4. Task queue initialization (`services/queue.py`)
5. Default admin user creation on first run

### Blueprint Organization

**API Blueprint** (`api/` prefix):
- `api/sms.py` - SMS endpoints (list, send single/bulk, get details)
- `api/decorators.py` - `@validate_json` decorator for request validation
- `api/responses.py` - Standardized API response helpers

**Web Blueprint** (no prefix):
- `web/auth.py` - `/login`, `/logout` (Flask-Login session-based auth)
- `web/sms.py` - `/`, `/compose`, `/history`, `/history/<id>`
- `web/admin.py` - `/admin/users/*` (admin-only user management)

### Service Layer

**HKTSMSService** (`services/hkt_sms.py`):
- Encapsulates SMS gateway interactions
- Requires `ConfigService` injection (initialized in app factory)
- Methods: `send_single()`, `send_bulk()`

**ConfigService** (`config/sms_config.py`):
- Manages SMS gateway configuration
- `get_sms_config()` provides defaults when env vars are not set:
  - Default base URL: `https://cst01.1010.com.hk/gateway/gateway.jsp`
  - Default application_id: `LabourDept`
  - Default sender_number: `852520702793127`

### Task Queue (`services/queue.py`)

In-memory threading-based queue for async SMS processing:
- Default: 4 worker threads
- Configurable max queue size (default: 1000)
- Tasks: `process_single_sms_task()`, `process_bulk_sms_task()`
- Use `enqueue_single_sms()` and `enqueue_bulk_sms()` to queue tasks

### Database Models

**User**: id, username, password_hash, token, is_admin, is_active, created_at
**Message**: id, user_id, content, status, created_at, sent_at, hkt_response
**Recipient**: id, message_id, phone, status, error_message

Statuses: pending, sent, failed, partial

## Commands

### Development Setup

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

### Running the Application

```bash
python run.py  # Runs on http://localhost:3570
```

### Mock SMS Provider

For testing without real SMS gateway:

```bash
python scripts/mock_sms_api.py  # Runs on http://127.0.0.1:5555
```

### Running Tests

```bash
pytest                              # All tests
pytest tests/test_api.py             # Single test file
pytest tests/test_api.py::test_list_messages_empty  # Specific test
pytest --cov=src --cov-report=term-missing  # With coverage
```

### Code Quality

```bash
ruff check .                        # Lint
ruff check . --fix                  # Auto-fix lint issues
ruff format .                       # Format code
```

### Installation

```bash
pip install -e .  # Editable mode for development
```

## Environment Variables

Required:
- `DATABASE_URL` - SQLAlchemy connection string
- `SMS_BASE_URL` - SMS gateway URL
- `SMS_APPLICATION_ID` - SMS API app ID
- `SMS_SENDER_NUMBER` - SMS sender number

Optional:
- `SECRET_KEY` - Flask session encryption (default: dev-secret-key)
- `SMS_QUEUE_WORKERS` - Worker thread count (default: 4)
- `SMS_QUEUE_MAX_SIZE` - Max queue size (default: 1000)

## Default Admin Account

Created automatically on first run:
- Username: `SMSadmin`
- Password: `SMSpass#12`

Change this immediately after first deployment.

## Phone Number Validation

Hong Kong format: 4 digits, optional space, 4 digits
- Valid: `1234 5678`, `12345678`
- Invalid: `1234-5678`, `123456789`

Helper: `utils/validation.validate_enquiry_number()`

## Authentication

- **Web UI**: Flask-Login session-based (`@login_required`, `@admin_required`)
- **API**: Bearer token (`Authorization: Bearer <token>`)
- Helper: `utils.admin.get_user_from_token()`

## HKT Timezone

Template filter `{{ dt|hkt }}` converts UTC to Hong Kong Time (UTC+8).
