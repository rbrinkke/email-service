#!/bin/bash
# File: deploy_email_system.sh
# Deploy FreeFace Email System

set -e

echo "🚀 Deploying FreeFace Email System..."

# Create directories
mkdir -p /opt/freeface/email/{logs,templates,config}
cd /opt/freeface/email

# Copy configuration files
cp docker-compose.yml .
cp Dockerfile.* .
cp requirements.txt .
cp redis.conf .

# Copy application files
cp email_system.py .
cp worker.py .
cp api.py .
cp monitor.py .
cp scheduler.py .
cp claude_guardian.py .
cp email_templates.py .
cp integration_examples.py .

# Set up environment
cat > .env << EOF
REDIS_HOST=redis-email
REDIS_PORT=6379
SENDGRID_API_KEY=${SENDGRID_API_KEY}
MAILGUN_API_KEY=${MAILGUN_API_KEY}
SMTP_PASSWORD=${SMTP_PASSWORD}
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
echo "🏥 Running health checks..."
curl -f http://localhost:8010/health || echo "❌ API health check failed"
curl -f http://localhost:8011/ || echo "❌ Monitor health check failed"

# Show status
echo "📊 Service status:"
docker-compose ps

echo "✅ FreeFace Email System deployed successfully!"
echo ""
echo "🌐 Monitoring Dashboard: http://localhost:8011"
echo "📡 API Endpoint: http://localhost:8010"
echo "📋 API Documentation: http://localhost:8010/docs"
echo ""
echo "🔗 Integration endpoints:"
echo "  POST /send - Send email"
echo "  POST /send/welcome - Send welcome email"  
echo "  POST /send/password-reset - Send password reset"
echo "  POST /send/group-notification - Send group notification"
echo "  GET /stats - Get system statistics"
echo ""
