# Quick Start Guide - Mock Servers

Get up and running with the mock servers in under 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- OR Python 3.11+ with pip

## Quick Start (Docker - Recommended)

### 1. Start All Mocks

```bash
cd mocks
docker-compose -f docker-compose.mocks.yml up -d
```

### 2. Verify Health

```bash
curl http://localhost:8001/health  # FreeFace API
curl http://localhost:8002/health  # SendGrid
curl http://localhost:8003/health  # Mailgun
curl http://localhost:8004/health  # Webhook Receiver
```

### 3. View Documentation

Open in your browser:
- **FreeFace API**: http://localhost:8001/docs
- **SendGrid API**: http://localhost:8002/docs
- **Mailgun API**: http://localhost:8003/docs
- **Webhook Receiver**: http://localhost:8004/docs

### 4. Run Tests

```bash
# Install httpx for testing
pip install httpx

# Run integration tests
python examples/test_with_mocks.py

# Or use cURL examples
bash examples/curl_examples.sh
```

### 5. Stop Mocks

```bash
docker-compose -f docker-compose.mocks.yml down
```

## Quick Start (Local Python)

### 1. Install Dependencies

```bash
cd mocks
pip install -r requirements.txt
```

### 2. Start Mocks (in separate terminals)

```bash
# Terminal 1: FreeFace API
python freeface_api/freeface_api_mock.py

# Terminal 2: SendGrid
python email_providers/sendgrid_mock.py

# Terminal 3: Mailgun
python email_providers/mailgun_mock.py

# Terminal 4: Webhook Receiver
python webhook_receiver/webhook_receiver_mock.py
```

### 3. Test

Follow steps 2-4 from Docker Quick Start above.

## Common Usage Examples

### FreeFace API

```bash
# List users
curl http://localhost:8001/api/v1/users?per_page=5 | jq

# Get specific user (replace {user_id} with actual ID from list)
curl http://localhost:8001/api/v1/users/{user_id} | jq

# List groups
curl http://localhost:8001/api/v1/groups | jq
```

### SendGrid API

```bash
# Send email
curl -X POST http://localhost:8002/v3/mail/send \
  -H "Authorization: Bearer SG.test_key_1234567890" \
  -H "Content-Type: application/json" \
  -d '{
    "personalizations": [{"to": [{"email": "user@example.com"}]}],
    "from": {"email": "sender@freeface.com"},
    "subject": "Test",
    "content": [{"type": "text/plain", "value": "Hello!"}]
  }' | jq

# Get stats
curl http://localhost:8002/v3/stats \
  -H "Authorization: Bearer SG.test_key_1234567890" | jq
```

### Mailgun API

```bash
# Send email
curl -X POST http://localhost:8003/sandbox123.mailgun.org/messages \
  -u api:test-mailgun-key-12345 \
  -F from="sender@freeface.com" \
  -F to="user@example.com" \
  -F subject="Test" \
  -F text="Hello!" | jq
```

### Webhook Receiver

```bash
# Send webhook
curl -X POST http://localhost:8004/webhooks/test \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "data": "example"}' | jq

# View history
curl http://localhost:8004/webhooks/history | jq
```

## API Keys for Testing

### SendGrid
- `SG.test_key_1234567890`
- `SG.mock_key_abcdefghij`

### Mailgun
- `api:test-mailgun-key-12345`
- `api:mock-mailgun-key-abcde`

### Mailgun Domains
- `sandbox123.mailgun.org`
- `mg.example.com`
- `mail.freeface.com`

## Advanced Features

### Error Simulation

```bash
# Simulate 404 error
curl http://localhost:8001/api/v1/users/test?simulate_error=404

# Simulate 500 error
curl http://localhost:8002/v3/stats?simulate_error=500
```

### Response Delay

```bash
# Add 1 second delay
curl http://localhost:8001/api/v1/users?delay_ms=1000
```

### Pagination

```bash
# Get page 2 with 10 items
curl http://localhost:8001/api/v1/users?page=2&per_page=10
```

## Troubleshooting

### Port Already in Use

Check what's using the ports:
```bash
netstat -tulpn | grep 800[1-4]
```

Change ports in `docker-compose.mocks.yml` if needed.

### Container Won't Start

Check logs:
```bash
docker-compose -f docker-compose.mocks.yml logs freeface-api-mock
```

Rebuild:
```bash
docker-compose -f docker-compose.mocks.yml build --no-cache
docker-compose -f docker-compose.mocks.yml up -d
```

### Health Check Fails

Test directly:
```bash
curl -v http://localhost:8001/health
```

Check container is running:
```bash
docker ps | grep mock
```

## Next Steps

- Read the full [README.md](README.md) for comprehensive documentation
- Explore the interactive API docs at `/docs` endpoints
- Run the example scripts in `examples/`
- Integrate mocks with your email service

## Support

For detailed documentation, see [README.md](README.md)

For issues, check the logs:
```bash
docker-compose -f docker-compose.mocks.yml logs -f
```
