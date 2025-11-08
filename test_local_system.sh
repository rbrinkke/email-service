#!/bin/bash
# Local Email System Startup and Test Script
# This script starts and tests the email system without Docker

set -e

echo "🚀 Starting FreeFace Email System (Local Mode)"
echo "=============================================="
echo

# Set environment variables
export REDIS_HOST=localhost
export REDIS_PORT=6379
export LOG_LEVEL=INFO
export SMTP_HOST=localhost
export SMTP_PORT=1025
export SMTP_USERNAME=test@example.com
export SMTP_PASSWORD=test_smtp_password
export SMTP_FROM_EMAIL=noreply@freeface.com
export SMTP_USE_TLS=false

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p /opt/email/logs /opt/email/templates logs

# Check Redis
echo "🔍 Checking Redis..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
else
    echo "❌ Redis is not running. Starting Redis..."
    redis-server --daemonize yes --port 6379 --dir /tmp
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis started successfully"
    else
        echo "❌ Failed to start Redis"
        exit 1
    fi
fi

# Check if Python dependencies are installed
echo "📦 Checking Python dependencies..."
python3 -c "import redis, fastapi, aiohttp" 2>/dev/null && echo "✅ Dependencies installed" || {
    echo "📥 Installing dependencies..."
    pip3 install -q -r requirements.txt
}

echo
echo "✨ Environment ready!"
echo
echo "To start the API:"
echo "  export REDIS_HOST=localhost && python3 api.py"
echo
echo "To start a worker:"
echo "  export REDIS_HOST=localhost && python3 worker.py"
echo
echo "To run tests:"
echo "  python3 test_local_email.py"
echo
