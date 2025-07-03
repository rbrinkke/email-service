#!/bin/bash
# Deploy FreeFace Email System locally

set -e

echo "🚀 Deploying FreeFace Email System..."

# Create .env file with test values (no real API keys needed for local testing)
cat > .env << EOF
REDIS_HOST=redis-email
REDIS_PORT=6379
SENDGRID_API_KEY=test_sendgrid_key
MAILGUN_API_KEY=test_mailgun_key
SMTP_PASSWORD=test_smtp_password
LOG_LEVEL=INFO
EOF

# Build and start services
echo "🔨 Building Docker images..."
docker compose build

echo "📦 Starting services..."
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Health check
echo "🏥 Checking system health..."
curl -s http://localhost:8010/health || echo "API not ready yet"

echo "📊 System status:"
docker compose ps

echo "✨ Email system deployed!"
echo "API: http://localhost:8010"
echo "Dashboard: http://localhost:8011"
echo "API Docs: http://localhost:8010/docs"