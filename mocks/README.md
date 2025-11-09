# Mock Server Infrastructure

Production-quality FastAPI mock servers for testing and development of the Email Service.

## Overview

This directory contains a complete mock server infrastructure with:

- **FreeFace API Mock** - Platform user and group management APIs
- **SendGrid Mock** - Email delivery API (v3)
- **Mailgun Mock** - Alternative email delivery API
- **Webhook Receiver** - Catch-all webhook testing server

All mocks follow consistent best practices:
- ✅ Production-quality FastAPI implementation
- ✅ Full OpenAPI/Swagger documentation
- ✅ Realistic mock data with Faker
- ✅ Error simulation support
- ✅ Response delay simulation
- ✅ Docker & Docker Compose ready
- ✅ Type-safe with Pydantic models
- ✅ Comprehensive logging
- ✅ Health check endpoints

## Quick Start

### Option 1: Docker Compose (Recommended)

Start all mock servers:
```bash
cd mocks
docker-compose -f docker-compose.mocks.yml up -d
```

Access the services:
- FreeFace API: http://localhost:8001/docs
- SendGrid API: http://localhost:8002/docs
- Mailgun API: http://localhost:8003/docs
- Webhook Receiver: http://localhost:8004/docs

### Option 2: Local Python

Install dependencies:
```bash
cd mocks
pip install -r requirements.txt
```

Run individual mocks:
```bash
# FreeFace API (port 8001)
python freeface_api/freeface_api_mock.py

# SendGrid API (port 8002)
python email_providers/sendgrid_mock.py

# Mailgun API (port 8003)
python email_providers/mailgun_mock.py

# Webhook Receiver (port 8004)
python webhook_receiver/webhook_receiver_mock.py
```

## Mock Server Details

### 1. FreeFace API Mock

**Port:** 8001
**Purpose:** Simulates FreeFace platform APIs for user/group management

**Key Endpoints:**
```
GET  /api/v1/users/{user_id}              - Get user profile
POST /api/v1/users/resolve                - Resolve multiple users
GET  /api/v1/groups/{group_id}            - Get group details
GET  /api/v1/groups/{group_id}/members    - List group members (paginated)
GET  /api/v1/users                        - List all users (paginated)
GET  /api/v1/groups                       - List all groups (paginated)
```

**Seed Data:**
- 50 realistic users with emails, profiles, avatars
- 10 groups with 5-20 members each
- Reproducible data (seed=42)

**Example Usage:**
```bash
# Get user profile
curl http://localhost:8001/api/v1/users/{user_id}

# Resolve multiple users
curl -X POST http://localhost:8001/api/v1/users/resolve \
  -H "Content-Type: application/json" \
  -d '{"user_ids": ["uuid1", "uuid2"]}'

# List group members (paginated)
curl http://localhost:8001/api/v1/groups/{group_id}/members?page=1&per_page=10

# Simulate error
curl http://localhost:8001/api/v1/users/invalid-id?simulate_error=404
```

### 2. SendGrid API Mock

**Port:** 8002
**Purpose:** Simulates SendGrid v3 Mail Send API

**Authentication:** Bearer token in Authorization header

**Valid API Keys:**
- `SG.test_key_1234567890`
- `SG.mock_key_abcdefghij`

**Key Endpoints:**
```
POST /v3/mail/send        - Send email
GET  /v3/stats            - Email statistics
GET  /v3/messages         - List sent messages
GET  /v3/webhooks/events  - Webhook events
```

**Example Usage:**
```bash
# Send email
curl -X POST http://localhost:8002/v3/mail/send \
  -H "Authorization: Bearer SG.test_key_1234567890" \
  -H "Content-Type: application/json" \
  -d '{
    "personalizations": [{
      "to": [{"email": "user@example.com", "name": "John Doe"}]
    }],
    "from": {"email": "sender@freeface.com", "name": "FreeFace"},
    "subject": "Test Email",
    "content": [{
      "type": "text/plain",
      "value": "Hello World"
    }]
  }'

# Get stats
curl http://localhost:8002/v3/stats \
  -H "Authorization: Bearer SG.test_key_1234567890"

# List sent messages
curl http://localhost:8002/v3/messages \
  -H "Authorization: Bearer SG.test_key_1234567890"
```

### 3. Mailgun API Mock

**Port:** 8003
**Purpose:** Simulates Mailgun Messages API

**Authentication:** Basic Auth with `api:<key>`

**Valid API Keys:**
- `api:test-mailgun-key-12345`
- `api:mock-mailgun-key-abcde`

**Valid Domains:**
- `sandbox123.mailgun.org`
- `mg.example.com`
- `mail.freeface.com`

**Key Endpoints:**
```
POST /{domain}/messages    - Send email
GET  /{domain}/events      - Get events
GET  /v3/domains           - List domains
```

**Example Usage:**
```bash
# Send email (Basic Auth)
curl -X POST http://localhost:8003/sandbox123.mailgun.org/messages \
  -u api:test-mailgun-key-12345 \
  -F from="sender@freeface.com" \
  -F to="user@example.com" \
  -F subject="Test Email" \
  -F text="Hello World"

# Get events
curl http://localhost:8003/sandbox123.mailgun.org/events \
  -u api:test-mailgun-key-12345

# List domains
curl http://localhost:8003/v3/domains \
  -u api:test-mailgun-key-12345
```

### 4. Webhook Receiver Mock

**Port:** 8004
**Purpose:** Catch-all webhook receiver for testing

**Authentication:** None (testing only!)

**Key Endpoints:**
```
POST   /webhooks/{path}      - Receive webhook (any path)
GET    /webhooks/history     - View received webhooks
DELETE /webhooks/history     - Clear webhook history
GET    /webhooks/stats       - Webhook statistics
```

**Example Usage:**
```bash
# Send webhook
curl -X POST http://localhost:8004/webhooks/sendgrid \
  -H "Content-Type: application/json" \
  -d '{"event": "delivered", "email": "user@example.com"}'

# View webhook history
curl http://localhost:8004/webhooks/history

# Get webhook stats
curl http://localhost:8004/webhooks/stats

# Clear history
curl -X DELETE http://localhost:8004/webhooks/history
```

## Advanced Features

### Error Simulation

All mocks support error simulation via query parameter:

```bash
# Simulate 404 Not Found
curl http://localhost:8001/api/v1/users/test?simulate_error=404

# Simulate 500 Internal Server Error
curl http://localhost:8002/v3/mail/send?simulate_error=500

# Simulate 429 Rate Limit
curl http://localhost:8003/v3/domains?simulate_error=429
```

### Response Delay Simulation

Simulate network latency:

```bash
# Add 1 second delay
curl http://localhost:8001/api/v1/users?delay_ms=1000

# Add 500ms delay
curl http://localhost:8002/v3/stats?delay_ms=500
```

### Pagination

All list endpoints support pagination:

```bash
# Get page 2 with 10 items per page
curl http://localhost:8001/api/v1/users?page=2&per_page=10

# Get first 5 groups
curl http://localhost:8001/api/v1/groups?page=1&per_page=5
```

## Architecture

```
mocks/
├── common/                           # Shared utilities
│   ├── base_mock.py                 # Base class for all mocks
│   ├── mock_data_generator.py       # Realistic data generation
│   ├── error_simulator.py           # Error simulation
│   └── middleware.py                # Logging, delay simulation
│
├── freeface_api/                    # FreeFace API mock
│   ├── freeface_api_mock.py        # Main server
│   └── models.py                    # Pydantic models
│
├── email_providers/                 # Email provider mocks
│   ├── sendgrid_mock.py            # SendGrid API
│   └── mailgun_mock.py             # Mailgun API
│
├── webhook_receiver/                # Webhook testing
│   └── webhook_receiver_mock.py    # Webhook receiver
│
├── examples/                        # Example scripts
│   ├── test_with_mocks.py          # Integration test examples
│   └── curl_examples.sh            # cURL examples
│
├── docker-compose.mocks.yml        # Docker orchestration
├── Dockerfile.mock                  # Docker image
├── requirements.txt                 # Dependencies
└── README.md                        # This file
```

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
# Mock behavior
MOCK_LOG_LEVEL=INFO
MOCK_RESPONSE_DELAY_MS=0
MOCK_ERROR_RATE=0.0

# Ports (local development)
FREEFACE_API_PORT=8001
SENDGRID_API_PORT=8002
MAILGUN_API_PORT=8003
WEBHOOK_RECEIVER_PORT=8004
```

## Integration with Email Service

### Update Email Service Configuration

Point your email service to the mocks:

```bash
# In your main .env file
FREEFACE_API_URL=http://localhost:8001
SENDGRID_API_URL=http://localhost:8002
MAILGUN_API_URL=http://localhost:8003
WEBHOOK_URL=http://localhost:8004/webhooks/email
```

### Testing Workflow

1. Start all mocks:
   ```bash
   docker-compose -f mocks/docker-compose.mocks.yml up -d
   ```

2. Run email service:
   ```bash
   docker-compose up -d
   ```

3. Test integration:
   ```bash
   python examples/test_with_mocks.py
   ```

4. View webhook history:
   ```bash
   curl http://localhost:8004/webhooks/history
   ```

## Docker Commands

```bash
# Start all mocks
docker-compose -f docker-compose.mocks.yml up -d

# Start specific mock
docker-compose -f docker-compose.mocks.yml up -d freeface-api-mock

# View logs
docker-compose -f docker-compose.mocks.yml logs -f

# View logs for specific mock
docker-compose -f docker-compose.mocks.yml logs -f sendgrid-mock

# Restart all mocks
docker-compose -f docker-compose.mocks.yml restart

# Stop all mocks
docker-compose -f docker-compose.mocks.yml down

# Rebuild and restart
docker-compose -f docker-compose.mocks.yml up -d --build

# Check health
docker-compose -f docker-compose.mocks.yml ps
```

## Development

### Adding a New Mock

1. Create mock file: `mocks/my_service/my_service_mock.py`
2. Inherit from `BaseMockServer`
3. Implement `_setup_routes()`
4. Add to `docker-compose.mocks.yml`
5. Document in README

Example:
```python
from common.base_mock import BaseMockServer

class MyServiceMock(BaseMockServer):
    def __init__(self):
        super().__init__(
            title="My Service Mock",
            description="Mock for My Service",
            version="1.0.0"
        )
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/api/data")
        async def get_data():
            return {"data": "example"}
```

### Running Tests

```bash
# Unit tests for mocks
pytest tests/test_mocks.py

# Integration tests
python examples/test_with_mocks.py

# Load testing
locust -f tests/locustfile.py --host=http://localhost:8001
```

## Best Practices

1. **Use Docker Compose** for consistent environments
2. **Check health endpoints** before running tests
3. **Clear webhook history** between test runs
4. **Use error simulation** to test error handling
5. **Use delay simulation** to test timeouts
6. **Review OpenAPI docs** at `/docs` for each mock
7. **Check logs** when debugging issues

## Troubleshooting

### Mock not starting

```bash
# Check logs
docker-compose -f docker-compose.mocks.yml logs freeface-api-mock

# Check port conflicts
netstat -tulpn | grep 800[1-4]

# Rebuild image
docker-compose -f docker-compose.mocks.yml build freeface-api-mock
```

### Health check failing

```bash
# Test health endpoint directly
curl http://localhost:8001/health

# Check container status
docker ps -a | grep mock
```

### Authentication errors

- **SendGrid**: Use `Authorization: Bearer SG.test_key_1234567890`
- **Mailgun**: Use Basic Auth with `-u api:test-mailgun-key-12345`
- **FreeFace**: No authentication required (add if needed)

## Support

For issues or questions:
1. Check the OpenAPI docs at `http://localhost:800X/docs`
2. Review logs with `docker-compose logs -f`
3. Check examples in `examples/` directory
4. Review this README

## License

Same as parent Email Service project.
