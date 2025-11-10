# 📨 Email Service Integration Examples

Complete integration examples for calling the FreeFace Email Service from your applications.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Python Examples](#python-examples)
3. [Node.js Examples](#nodejs-examples)
4. [cURL Examples](#curl-examples)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)

---

## Quick Start

### Prerequisites

1. **Get a service token** from your .env file or generate one:
   ```bash
   python scripts/generate_service_token.py --service your-app
   ```

2. **Set as environment variable:**
   ```bash
   export SERVICE_TOKEN_YOUR_APP=st_dev_abc123...
   ```

3. **Email service URL:**
   - Development: `http://email-api:8010` (within Docker network)
   - Production: `http://your-email-service-host:8010`

---

## Python Examples

### Using `httpx` (Async - Recommended)

```python
import httpx
import os
from typing import List

# Configuration
EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL", "http://email-api:8010")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN_YOUR_APP")


class EmailClient:
    """
    Async client for FreeFace Email Service

    Example:
        async with EmailClient() as client:
            job_id = await client.send_email(
                recipients="user@example.com",
                template="welcome",
                data={"name": "John"}
            )
    """

    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = base_url or EMAIL_SERVICE_URL
        self.token = token or SERVICE_TOKEN

        if not self.token:
            raise ValueError("Service token required. Set SERVICE_TOKEN_YOUR_APP env var")

        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-Service-Token": self.token},
            timeout=30.0
        )
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    async def send_email(
        self,
        recipients: str | List[str],
        template: str,
        data: dict = None,
        priority: str = "medium",
        provider: str = "smtp"
    ) -> str:
        """
        Send email via email service

        Args:
            recipients: Email address or list of addresses
            template: Template name (e.g., "welcome", "password_reset")
            data: Template variables
            priority: "high", "medium", or "low"
            provider: "smtp", "sendgrid", "mailgun", or "aws_ses"

        Returns:
            Job ID (str)

        Raises:
            httpx.HTTPStatusError: If API returns error
        """
        response = await self.client.post(
            "/send",
            json={
                "recipients": recipients,
                "template": template,
                "data": data or {},
                "priority": priority,
                "provider": provider
            }
        )

        response.raise_for_status()
        result = response.json()
        return result["job_id"]

    async def get_stats(self) -> dict:
        """
        Get email system statistics

        Returns:
            Statistics dictionary
        """
        response = await self.client.get("/stats")
        response.raise_for_status()
        return response.json()


# Usage example
async def main():
    async with EmailClient() as email:
        # Send welcome email
        job_id = await email.send_email(
            recipients="newuser@example.com",
            template="welcome",
            data={
                "name": "John Doe",
                "verification_link": "https://freeface.com/verify/abc123"
            },
            priority="high"
        )
        print(f"Welcome email queued: {job_id}")

        # Send password reset email
        job_id = await email.send_email(
            recipients="user@example.com",
            template="password_reset",
            data={
                "reset_link": "https://freeface.com/reset/xyz789"
            },
            priority="high"
        )
        print(f"Password reset email queued: {job_id}")

        # Send custom newsletter
        job_id = await email.send_email(
            recipients=["user1@example.com", "user2@example.com"],
            template="monthly_newsletter",
            data={
                "month": "November",
                "highlights": ["Feature 1", "Feature 2"]
            },
            priority="low"
        )
        print(f"Newsletter queued: {job_id}")

        # Get statistics
        stats = await email.get_stats()
        print(f"Queue size: {stats['queue_high'] + stats['queue_medium'] + stats['queue_low']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Using `requests` (Sync)

```python
import requests
import os

EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL", "http://email-api:8010")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN_YOUR_APP")

def send_email(recipients, template, data=None, priority="medium"):
    """
    Send email via email service (synchronous)

    Args:
        recipients: Email address or list of addresses
        template: Template name
        data: Template variables
        priority: "high", "medium", or "low"

    Returns:
        Job ID (str)
    """
    headers = {
        "X-Service-Token": SERVICE_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "recipients": recipients,
        "template": template,
        "data": data or {},
        "priority": priority,
        "provider": "smtp"
    }

    response = requests.post(
        f"{EMAIL_SERVICE_URL}/send",
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()
    return response.json()["job_id"]


# Usage
if __name__ == "__main__":
    job_id = send_email(
        recipients="user@example.com",
        template="welcome",
        data={"name": "John"},
        priority="high"
    )
    print(f"Email queued: {job_id}")
```

---

## Node.js Examples

### Using `axios` (Async/Await)

```javascript
const axios = require('axios');

// Configuration
const EMAIL_SERVICE_URL = process.env.EMAIL_SERVICE_URL || 'http://email-api:8010';
const SERVICE_TOKEN = process.env.SERVICE_TOKEN_YOUR_APP;

class EmailClient {
    constructor(baseURL = EMAIL_SERVICE_URL, token = SERVICE_TOKEN) {
        if (!token) {
            throw new Error('Service token required. Set SERVICE_TOKEN_YOUR_APP env var');
        }

        this.client = axios.create({
            baseURL,
            headers: {
                'X-Service-Token': token,
                'Content-Type': 'application/json'
            },
            timeout: 30000
        });
    }

    /**
     * Send email via email service
     *
     * @param {string|string[]} recipients - Email address(es)
     * @param {string} template - Template name
     * @param {Object} data - Template variables
     * @param {string} priority - "high", "medium", or "low"
     * @param {string} provider - "smtp", "sendgrid", etc.
     * @returns {Promise<string>} Job ID
     */
    async sendEmail(recipients, template, data = {}, priority = 'medium', provider = 'smtp') {
        try {
            const response = await this.client.post('/send', {
                recipients,
                template,
                data,
                priority,
                provider
            });

            return response.data.job_id;
        } catch (error) {
            console.error('Email send failed:', error.response?.data || error.message);
            throw error;
        }
    }

    /**
     * Get email statistics
     */
    async getStats() {
        const response = await this.client.get('/stats');
        return response.data;
    }
}

// Usage example
async function main() {
    const email = new EmailClient();

    try {
        // Send welcome email
        const jobId = await email.sendEmail(
            'newuser@example.com',
            'welcome',
            {
                name: 'John Doe',
                verification_link: 'https://freeface.com/verify/abc123'
            },
            'high'
        );
        console.log(`Welcome email queued: ${jobId}`);

        // Send password reset email
        const resetJobId = await email.sendEmail(
            'user@example.com',
            'password_reset',
            {
                reset_link: 'https://freeface.com/reset/xyz789'
            },
            'high'
        );
        console.log(`Password reset email queued: ${resetJobId}`);

        // Send custom newsletter
        const customJobId = await email.sendEmail(
            ['user1@example.com', 'user2@example.com'],
            'monthly_newsletter',
            {
                month: 'November',
                highlights: ['Feature 1', 'Feature 2']
            },
            'low'
        );
        console.log(`Newsletter queued: ${customJobId}`);

        // Get statistics
        const stats = await email.getStats();
        console.log(`Queue size: ${stats.queue_high + stats.queue_medium + stats.queue_low}`);

    } catch (error) {
        console.error('Error:', error.message);
    }
}

main();
```

---

## cURL Examples

### Send Welcome Email

```bash
#!/bin/bash

# Configuration
EMAIL_SERVICE_URL="http://email-api:8010"
SERVICE_TOKEN="st_dev_abc123..."

# Send welcome email
curl -X POST "${EMAIL_SERVICE_URL}/send" \
  -H "X-Service-Token: ${SERVICE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": "user@example.com",
    "template": "welcome",
    "data": {
      "name": "John Doe",
      "verification_link": "https://freeface.com/verify/abc123"
    },
    "priority": "high",
    "provider": "smtp"
  }'
```

### Send Password Reset Email

```bash
# Send password reset email
curl -X POST "${EMAIL_SERVICE_URL}/send" \
  -H "X-Service-Token: ${SERVICE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": "user@example.com",
    "template": "password_reset",
    "data": {
      "reset_link": "https://freeface.com/reset/xyz789"
    },
    "priority": "high",
    "provider": "smtp"
  }'
```

### Send Custom Newsletter

```bash
# Send custom newsletter to multiple recipients
curl -X POST "${EMAIL_SERVICE_URL}/send" \
  -H "X-Service-Token: ${SERVICE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": ["user1@example.com", "user2@example.com"],
    "template": "monthly_newsletter",
    "data": {
      "month": "November",
      "highlights": ["Feature 1", "Feature 2"]
    },
    "priority": "low",
    "provider": "smtp"
  }'
```

### Get Statistics

```bash
curl -X GET "${EMAIL_SERVICE_URL}/stats" \
  -H "X-Service-Token: ${SERVICE_TOKEN}"
```

### Health Check (No Auth Required)

```bash
curl -X GET "${EMAIL_SERVICE_URL}/health"
```

---

## Error Handling

### Common Errors

#### 401 Unauthorized

```json
{
  "detail": {
    "error": "invalid_token",
    "message": "Service token not recognized. Check token is correct and service is configured."
  }
}
```

**Solution:** Check your service token is correct and configured in email service's .env file.

#### 401 Missing Token

```json
{
  "detail": {
    "error": "authentication_required",
    "message": "Service token required. Provide X-Service-Token header.",
    "docs": "See SERVICE_AUTHENTICATION.md for integration guide"
  }
}
```

**Solution:** Add `X-Service-Token` header to your request.

#### 500 Internal Server Error

```json
{
  "detail": "Error sending email: <error_message>"
}
```

**Solution:** Check email service logs for detailed error information.

### Error Handling Best Practices

```python
import httpx
import logging

logger = logging.getLogger(__name__)

async def send_email_with_retry(recipients, template, data, max_retries=3):
    """
    Send email with automatic retry on failure

    Args:
        recipients: Email recipient(s)
        template: Template name
        data: Template data
        max_retries: Maximum number of retry attempts

    Returns:
        Job ID or None if all retries failed
    """
    for attempt in range(max_retries):
        try:
            async with EmailClient() as client:
                job_id = await client.send_email(recipients, template, data)
                logger.info(f"Email sent successfully: {job_id}")
                return job_id

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Authentication error - don't retry
                logger.error(f"Authentication failed: {e.response.json()}")
                return None

            elif e.response.status_code >= 500:
                # Server error - retry
                logger.warning(f"Server error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue

            else:
                # Client error - don't retry
                logger.error(f"Client error: {e.response.json()}")
                return None

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return None

    logger.error(f"All {max_retries} retry attempts failed")
    return None
```

---

## Best Practices

### 1. **Token Security**

✅ **DO:**
- Store tokens in environment variables
- Use different tokens for dev/staging/production
- Rotate tokens every 90 days
- Never commit tokens to git

❌ **DON'T:**
- Hardcode tokens in source code
- Share tokens between services
- Log full token values
- Expose tokens in error messages

### 2. **Error Handling**

✅ **DO:**
- Implement retry logic with exponential backoff
- Log errors with context
- Handle network timeouts
- Validate responses

❌ **DON'T:**
- Retry on 401 errors (authentication will always fail)
- Retry indefinitely
- Ignore error responses
- Assume success without checking status

### 3. **Performance**

✅ **DO:**
- Use connection pooling
- Set reasonable timeouts (30s recommended)
- Send bulk emails as single request
- Cache email client instances

❌ **DON'T:**
- Create new client for each request
- Use infinite timeouts
- Send emails synchronously in request handlers
- Block application on email sending

### 4. **Testing**

✅ **DO:**
- Use mock email client in unit tests
- Test with SERVICE_AUTH_ENABLED=false in development
- Verify job IDs are returned
- Test error scenarios

❌ **DON'T:**
- Send real emails in tests
- Skip error case testing
- Assume email delivery (async process)

---

## Support

- **Documentation:** See `SERVICE_AUTHENTICATION.md` for authentication details
- **Monitoring:** Check `/health` endpoint for service status
- **Logs:** `docker-compose logs email-api` for debugging

---

**Last Updated:** 2025-11-08
**Version:** 1.0.0
