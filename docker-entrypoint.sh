#!/bin/bash
set -e

# Ensure instance directory exists and has correct permissions
mkdir -p /app/instance
#chown -R appuser:appuser /app/instance
chmod 777 /app/instance

# Fix permissions on database file if it exists
if [ -f /app/instance/sms.db ]; then
#    chown appuser:appuser /app/instance/sms.db
    chmod 777 /app/instance/sms.db
fi

# Switch to non-root user and run the command
#exec gosu appuser "$@"
