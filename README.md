# smspanel

A Python SMS management application with web UI and REST API for sending and tracking SMS messages.

## Objectives

This application provides a comprehensive SMS management system with the following objectives:

1. **SMS Composition & Delivery** - Compose and send SMS messages to single or multiple recipients with automatic format validation
2. **Message Tracking** - Track delivery status (pending, sent, failed) for each message and individual recipients
3. **User Management** - Admin interface for complete user lifecycle management (create, modify password, enable/disable, delete)
4. **API Access** - RESTful API for programmatic SMS sending with token-based authentication
5. **Hong Kong Integration** - Built-in timezone conversion (UTC to HKT) and SMS gateway integration
6. **Testing Support** - Mock SMS provider for local development and testing

## Features

- **SMS Composition & Sending**: Create and send SMS messages to single or multiple recipients
- **Message History**: Track sent messages with status (pending, sent, failed, partial)
- **User Management**: Admin interface for user CRUD operations
- **Authentication**: Web login and API token-based authentication
- **Hong Kong Time**: Built-in timezone conversion (UTC to HKT)
- **Mock SMS API**: Testing mode simulates SMS gateway

## System Functions

### SMS Management
- **Compose**: Create new SMS messages with content and recipients
- **Send**: Send SMS via SMS gateway (real or mock)
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
  -d '{"username":"SMSadmin","password":"<your-password>"}'
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

## Quick Start

### Fresh Installation

```bash
# Clone and enter directory
git clone <repo-url>
cd smspanel

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and set required variables (see Configuration below)
# At minimum, set SECRET_KEY (at least 32 characters)
nano .env

# Run the application
python run.py
```

### Admin Account Setup

On first run, an admin account is automatically created:

| Field | Value |
|-------|--------|
| Username | `SMSadmin` |
| Password | **Auto-generated random password** |

**In development mode**, the generated password is printed to the console:
```
[DEV] Generated admin password: Xy7mN4qR9ZpL2wBc
```

**To set a known password**, set the `ADMIN_PASSWORD` environment variable before first run:

```bash
export ADMIN_PASSWORD="YourSecurePassword123"
python run.py
```

Or change the password via the web UI after logging in:
1. Go to `/admin/users`
2. Click "Change Password" for the admin user

### Creating Additional Users

1. Log in as admin
2. Navigate to `/admin/users`
3. Click "Create New User"
4. Fill in username, password, and optionally check "Admin Account"

### First SMS

1. Log in at `http://localhost:3570/login`
2. Click "Compose"
3. Enter recipients (one per line, e.g., `1234 5678`)
4. Enter message content
5. Enter enquiry number (4 digits, optional space, 4 digits)
6. Click "Send SMS"

## Mock SMS Provider

To run mock SMS provider (required for testing):

```bash
source .venv/bin/activate
python scripts/mock_sms_api.py
```

The mock server runs on `http://127.0.0.1:5555/gateway/gateway.jsp`

## Deployment Procedure

### Prerequisites

1. **Python 3.12+** installed on target server
2. **Environment variables** configured (see Configuration section)
3. **Production database** location secured
4. **SMS gateway credentials** obtained

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

# SMS Gateway (production)
SMS_BASE_URL=https://cst01.1010.com.hk/gateway/gateway.jsp
SMS_APPLICATION_ID=YourAppID
SMS_SENDER_NUMBER=YourSenderNumber
```

Generate secure keys using:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 3. Initialize Database

```bash
# Set SECRET_KEY and ADMIN_PASSWORD before first run
export SECRET_KEY="your-secure-key-at-least-32-chars"
export ADMIN_PASSWORD="YourSecurePassword123"

# Run app once to create database and admin user
python run.py
# Then press Ctrl+C to stop
```

**Important**: After first run:
- Change the admin password if you used a temporary one
- Generate a new admin API token via admin panel if needed

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

An admin account is created automatically on first run:

| Field | Value |
|-------|--------|
| Username | `SMSadmin` |
| Password | **Auto-generated random password** |
| Role | Admin |
| Status | Active |

**Security Note:**
- In development: password is printed to console on first run
- In production: password is auto-generated and logged as a warning
- To set a known password, set `ADMIN_PASSWORD` environment variable before first run

**Important**: Change the admin password via the web UI after first deployment if using auto-generated password!

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
│   └── smspanel/
│       ├── models.py        # Database models (User, Message, Recipient, DeadLetterMessage)
│       ├── config.py        # Configuration classes
│       ├── __init__.py      # App factory
│       ├── api/             # REST API endpoints
│       │   ├── __init__.py
│       │   └── sms.py       # SMS endpoints
│       ├── web/             # Web UI
│       │   ├── __init__.py
│       │   ├── auth.py      # Login/logout
│       │   ├── sms.py       # SMS composition/history
│       │   ├── admin.py     # User management (admin only)
│       │   └── dead_letter.py  # Dead letter queue management
│       ├── services/        # Business logic
│       │   ├── hkt_sms.py   # SMS service with retry logic
│       │   ├── queue.py     # Async task queue
│       │   └── dead_letter.py  # Dead letter queue service
│       └── templates/       # Jinja2 templates
│           ├── admin/
│           │   ├── users.html
│           │   └── dead_letter.html
│           └── *.html
├── instance/               # SQLite database (auto-created)
├── static/                 # CSS, JS assets
├── tests/                  # Pytest tests
├── scripts/                # Utility scripts
│   └── mock_sms_api.py     # Mock SMS gateway for testing
├── run.py                  # Application entry point
└── pyproject.toml          # Project config
```

## Database

SQLite database (`sms.db`) is auto-created in `instance/` directory on first run.

### SQLite (Development - Default)

```bash
DATABASE_URL=sqlite:///sms.db
```

### MySQL (Production Recommended)

```bash
DATABASE_URL=mysql+pymysql://username:password@hostname:3306/database_name
```

PyMySQL is used as the MySQL driver (pure Python, no system dependencies).

### Connection Pool Settings

For MySQL/PostgreSQL, configure connection pooling:

| Setting | Description | Default |
|---------|-------------|---------|
| `SQLALCHEMY_POOL_SIZE` | Number of connections to maintain | 10 |
| `SQLALCHEMY_POOL_MAX_OVERFLOW` | Max additional connections | 20 |
| `SQLALCHEMY_POOL_RECYCLE` | Recycle connections after (seconds) | 3600 |
| `SQLALCHEMY_POOL_PRE_PING` | Verify connections before use | true |

### Persistent Task Queue

Tasks are now persisted in the database for reliability:

- Tasks survive application restarts
- Failed tasks can be retried
- Queue statistics available at `/admin/dead-letter`

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
| `SMS_BASE_URL` | SMS gateway | `SMS_BASE_URL` |
| `SMS_APPLICATION_ID` | SMS app ID | `SMS_APPLICATION_ID` |
| `SMS_SENDER_NUMBER` | SMS sender number | `SMS_SENDER_NUMBER` |

Optional settings (with defaults):

| Setting | Description | Default | Environment Variable |
|---------|-------------|----------|---------------------|
| `SECRET_KEY` | Flask session key (min 32 chars) | None (required) | `SECRET_KEY` |
| `ADMIN_PASSWORD` | Admin user password | Auto-generated | `ADMIN_PASSWORD` |

## Phone Number Format

Hong Kong phone numbers must match format: `4 digits, optional space, 4 digits`

**Valid formats:**
- `1234 5678`
- `12345678`

**Invalid formats:**
- `1234-5678`
- `123456789`
- `12 3456`

## Retry Logic

The SMS service uses exponential backoff retry logic for transient failures:

- **Max Attempts**: 3 retries per message
- **Backoff**: Exponential with 2s minimum, 10s maximum
- **Retried Errors**: Connection errors, timeouts

Retry logic is implemented using the `tenacity` library.

## Dead Letter Queue

Failed SMS messages that cannot be delivered after all retry attempts are stored in the dead letter queue for later review and manual retry.

### Accessing Dead Letter Queue

1. Log in as admin
2. Navigate to `/admin/dead-letter`

### Dead Letter Queue Features

- **View All**: Browse all failed messages with filtering by status
- **Retry Individual**: Retry specific failed messages
- **Retry All**: Retry all pending messages at once
- **Abandon**: Mark messages as permanently failed

### Message Status

| Status | Description |
|--------|-------------|
| `pending` | Ready for retry |
| `retried` | Successfully resent |
| `abandoned` | Permanently failed after max retries |
