# smspanel

A Python SMS management application with web UI and REST API for sending and tracking SMS messages via HKT SMS gateway.

## Objectives

This application provides a comprehensive SMS management system with the following objectives:

1. **SMS Composition & Delivery** - Compose and send SMS messages to single or multiple recipients with automatic format validation
2. **Message Tracking** - Track delivery status (pending, sent, failed) for each message and individual recipients
3. **User Management** - Admin interface for complete user lifecycle management (create, modify password, enable/disable, delete)
4. **API Access** - RESTful API for programmatic SMS sending with token-based authentication
5. **Hong Kong Integration** - Built-in timezone conversion (UTC to HKT) and HKT SMS gateway integration
6. **Testing Support** - Mock SMS provider for local development and testing

## Features

- **SMS Composition & Sending**: Create and send SMS messages to single or multiple recipients
- **Message History**: Track sent messages with status (pending, sent, failed, partial)
- **User Management**: Admin interface for user CRUD operations
- **Authentication**: Web login and API token-based authentication
- **Hong Kong Time**: Built-in timezone conversion (UTC to HKT)
- **Mock HKT API**: Testing mode simulates HKT SMS gateway

## System Functions

### SMS Management
- **Compose**: Create new SMS messages with content and recipients
- **Send**: Send SMS via HKT SMS gateway (real or mock)
- **Track**: Monitor delivery status per message and per recipient
- **History**: View and search past messages with filters
- **Detail**: View full message details including recipient status

### User Management (Admin Only)
- **Create**: Add new users with admin privileges
- **Password Change**: Update user passwords
- **Enable/Disable**: Toggle user account status
- **Delete**: Remove users (with self-protection)
- **Token Management**: Regenerate API tokens for users

### Authentication
- **Web Login**: Session-based authentication for web UI
- **API Token**: Bearer token authentication for REST API
- **Auto-Admin**: Default admin account created on first run

## Web Endpoints

| Route | Method | Auth | Description |
|-------|---------|--------|-------------|
| `/login` | GET, POST | Login page and form submission |
| `/logout` | GET | User logout |
| `/` | GET | Required | Dashboard with recent messages |
| `/compose` | GET, POST | Required | Compose and send SMS |
| `/history` | GET | Required | Message history with search/filter |
| `/history/<id>` | GET | Required | View message details |
| `/admin/users` | GET | Required, Admin | List all users |
| `/admin/users/create` | GET, POST | Required, Admin | Create new user |
| `/admin/users/<id>/password` | GET, POST | Required, Admin | Change user password |
| `/admin/users/<id>/toggle` | POST | Required, Admin | Enable/disable user |
| `/admin/users/<id>/delete` | GET, POST | Required, Admin | Delete user |
| `/admin/users/<id>/regenerate_token` | POST | Required, Admin | Regenerate API token |

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|--------|-------------|
| `/api/sms` | GET | Token Required | List messages (paginated) |
| `/api/sms` | POST | Token Required | Send single SMS |
| `/api/sms/send-bulk` | POST | Token Required | Send bulk SMS |
| `/api/sms/<id>` | GET | Token Required | Get message details |
| `/api/sms/<id>/recipients` | GET | Token Required | Get message recipients |

### API Request Example

**Login:**
```bash
curl -X POST http://localhost:3570/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"SMSadmin","password":"SMSpass#12"}'
```

**Send SMS:**
```bash
curl -X POST http://localhost:3570/api/sms \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"recipient":"1234 5678","content":"Hello World"}'
```

## Development Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run app
python run.py
```

The app will start on `http://localhost:3570`

## Mock SMS Provider

To run mock HKT SMS provider (required for testing):

```bash
source .venv/bin/activate
python scripts/mock_hkt_api.py
```

The mock server runs on `http://127.0.0.1:5555/gateway/gateway.jsp`

## Deployment Procedure

### Prerequisites

1. **Python 3.12+** installed on target server
2. **Environment variables** configured (see Configuration section)
3. **Production database** location secured
4. **HKT SMS gateway credentials** obtained

### Deployment Steps

#### 1. Prepare Production Environment

```bash
# Clone repository
git clone <repo-url>
cd smspanel

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment Variables

Create `.env` file in project root:

```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=<generate-strong-random-key>

# Database
DATABASE_URL=sqlite:///instance/sms.db

# HKT SMS Gateway (production)
HKT_BASE_URL=https://cst01.1010.com.hk/gateway/gateway.jsp
HKT_APPLICATION_ID=YourAppID
HKT_SENDER_NUMBER=YourSenderNumber
```

Generate secure keys using:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 3. Initialize Database

```bash
# Run app once to create database and admin user
FLASK_ENV=production python run.py
# Then press Ctrl+C to stop
```

**Important**: After first run:
- Change the default admin password (`SMSpass#12`)
- Generate a new admin API token via admin panel

#### 4. Production Server Setup

**Option A: Using Gunicorn (Recommended)**

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:3570 run:app
```

**Option B: Using uWSGI**

```bash
# Install uwsgi
pip install uwsgi

# Run with uwsgi
uwsgi --http 0.0.0.0:3570 --wsgi-file run.py --callable app
```

**Option C: Using systemd service**

Create `/etc/systemd/system/smspanel.service`:

```ini
[Unit]
Description=SMS Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/smspanel
Environment="PATH=/path/to/smspanel/.venv/bin"
ExecStart=/path/to/smspanel/.venv/bin/gunicorn -w 4 -b 0.0.0.0:3570 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable smspanel
sudo systemctl start smspanel
sudo systemctl status smspanel
```

#### 5. Reverse Proxy Configuration (Optional)

**Nginx:**

```nginx
server {
    listen 80;
    server_name sms.example.com;

    location / {
        proxy_pass http://127.0.0.1:3570;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

#### 6. SSL/TLS Configuration (Optional for Production)

Use certbot for free SSL:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d sms.example.com
```

#### 7. Database Backup Setup

Create cron job for daily backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cp /path/to/smspanel/instance/sms.db /backups/sms_$(date +\%Y\%m\%d).db
```

#### 8. Monitoring and Logging

- **Application logs**: Check stdout/stderr for errors
- **Database integrity**: Run periodic checks
- **Disk space**: Monitor `instance/` directory

## Default Admin Account

A fixed admin account is created on first run:

| Field | Value |
|-------|--------|
| Username | `SMSadmin` |
| Password | `SMSpass#12` |
| Role | Admin |
| Status | Active |

**Important**: Change this password immediately after first deployment!

## Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_example.py

# Lint
ruff check .

# Format
ruff format .
```

## Project Structure

```
smspanel/
├── src/                    # Source code
│   └── ccdemo/
│       ├── models.py        # Database models (User, Message, Recipient)
│       ├── config.py       # Configuration classes
│       ├── __init__.py     # App factory
│       ├── api/            # REST API endpoints
│       │   ├── __init__.py
│       │   └── sms.py     # SMS endpoints
│       ├── web/            # Web UI
│       │   ├── __init__.py
│       │   ├── auth.py     # Login/logout
│       │   ├── sms.py      # SMS composition/history
│       │   └── admin.py    # User management (admin only)
│       ├── services/        # Business logic
│       │   └── hkt_sms.py # HKT SMS service
│       └── templates/      # Jinja2 templates
│           ├── admin/
│           ├── *.html
├── instance/               # SQLite database (auto-created)
├── static/                # CSS, JS assets
├── tests/                 # Pytest tests
├── scripts/               # Utility scripts
│   └── mock_hkt_api.py
├── run.py                 # Application entry point
└── pyproject.toml         # Project config
```

## Database

SQLite database (`sms.db`) is auto-created in `instance/` directory on first run.

**Reset database:**
```bash
rm instance/sms.db
# Then restart app
```

## Configuration

Configuration is in `src/smspanel/config.py`. The following environment variables are required:

| Setting | Description | Environment Variable |
|---------|-------------|---------------------|
| `DATABASE_URL` | Database path | `DATABASE_URL` |
| `HKT_BASE_URL` | HKT SMS gateway | `HKT_BASE_URL` |
| `HKT_APPLICATION_ID` | HKT app ID | `HKT_APPLICATION_ID` |
| `HKT_SENDER_NUMBER` | HKT sender number | `HKT_SENDER_NUMBER` |

Optional settings (with defaults):

| Setting | Description | Default | Environment Variable |
|---------|-------------|----------|---------------------|
| `SECRET_KEY` | Flask session key | dev-secret-key | `SECRET_KEY` |

## Phone Number Format

Hong Kong phone numbers must match format: `4 digits, optional space, 4 digits`

**Valid formats:**
- `1234 5678`
- `12345678`

**Invalid formats:**
- `1234-5678`
- `123456789`
- `12 3456`
