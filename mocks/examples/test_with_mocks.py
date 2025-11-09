#!/usr/bin/env python3
# File: mocks/examples/test_with_mocks.py
# Integration test examples using mock servers

"""
Integration test examples for mock servers

This script demonstrates how to test your email service
against the mock servers.

Usage:
    python test_with_mocks.py
"""

import asyncio
import sys
from pathlib import Path

import httpx

# Configuration
FREEFACE_API_URL = "http://localhost:8001"
SENDGRID_API_URL = "http://localhost:8002"
MAILGUN_API_URL = "http://localhost:8003"
WEBHOOK_URL = "http://localhost:8004"

# Valid API keys (from mocks)
SENDGRID_API_KEY = "SG.test_key_1234567890"
MAILGUN_API_KEY = "api:test-mailgun-key-12345"
MAILGUN_DOMAIN = "sandbox123.mailgun.org"


async def test_freeface_api():
    """Test FreeFace API mock"""
    print("\n=== Testing FreeFace API Mock ===")

    async with httpx.AsyncClient() as client:
        # Health check
        print("\n1. Health check...")
        response = await client.get(f"{FREEFACE_API_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")

        # List users
        print("\n2. List users (first page)...")
        response = await client.get(
            f"{FREEFACE_API_URL}/api/v1/users",
            params={"page": 1, "per_page": 5}
        )
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Total users: {data['pagination']['total']}")
        print(f"   Retrieved: {len(data['data'])} users")

        # Get first user ID for subsequent tests
        user_id = data["data"][0]["id"] if data["data"] else None

        if user_id:
            # Get specific user
            print(f"\n3. Get user profile (ID: {user_id[:8]}...)...")
            response = await client.get(f"{FREEFACE_API_URL}/api/v1/users/{user_id}")
            print(f"   Status: {response.status_code}")
            user = response.json()
            print(f"   User: {user['full_name']} ({user['email']})")

            # Resolve multiple users
            print("\n4. Resolve multiple users...")
            response = await client.post(
                f"{FREEFACE_API_URL}/api/v1/users/resolve",
                json={"user_ids": [user_id, "nonexistent-id"]}
            )
            print(f"   Status: {response.status_code}")
            result = response.json()
            print(f"   Found: {len(result['users'])} users")
            print(f"   Not found: {len(result['not_found'])} users")

        # List groups
        print("\n5. List groups...")
        response = await client.get(
            f"{FREEFACE_API_URL}/api/v1/groups",
            params={"page": 1, "per_page": 3}
        )
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Total groups: {data['pagination']['total']}")

        group_id = data["data"][0]["id"] if data["data"] else None

        if group_id:
            # Get group members
            print(f"\n6. Get group members (ID: {group_id[:8]}...)...")
            response = await client.get(
                f"{FREEFACE_API_URL}/api/v1/groups/{group_id}/members",
                params={"page": 1, "per_page": 5}
            )
            print(f"   Status: {response.status_code}")
            data = response.json()
            print(f"   Total members: {data['pagination']['total']}")
            print(f"   Retrieved: {len(data['data'])} members")

        # Test error simulation
        print("\n7. Test error simulation (404)...")
        response = await client.get(
            f"{FREEFACE_API_URL}/api/v1/users/invalid-id",
            params={"simulate_error": 404}
        )
        print(f"   Status: {response.status_code} (expected 404)")

    print("\n✅ FreeFace API tests completed!")


async def test_sendgrid_api():
    """Test SendGrid API mock"""
    print("\n=== Testing SendGrid API Mock ===")

    async with httpx.AsyncClient() as client:
        # Health check
        print("\n1. Health check...")
        response = await client.get(f"{SENDGRID_API_URL}/health")
        print(f"   Status: {response.status_code}")

        # Send email
        print("\n2. Send email...")
        response = await client.post(
            f"{SENDGRID_API_URL}/v3/mail/send",
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}"},
            json={
                "personalizations": [
                    {
                        "to": [{"email": "user@example.com", "name": "Test User"}]
                    }
                ],
                "from": {"email": "sender@freeface.com", "name": "FreeFace"},
                "subject": "Test Email from Mock",
                "content": [
                    {
                        "type": "text/plain",
                        "value": "This is a test email from the SendGrid mock!"
                    }
                ]
            }
        )
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Message ID: {result['message_id']}")
        print(f"   Status: {result['status']}")

        # Get stats
        print("\n3. Get email statistics...")
        response = await client.get(
            f"{SENDGRID_API_URL}/v3/stats",
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}"}
        )
        print(f"   Status: {response.status_code}")
        stats = response.json()
        if stats.get("stats"):
            metrics = stats["stats"][0]["stats"][0]["metrics"]
            print(f"   Processed: {metrics.get('processed', 0)}")
            print(f"   Delivered: {metrics.get('delivered', 0)}")

        # Test invalid API key
        print("\n4. Test invalid API key...")
        response = await client.post(
            f"{SENDGRID_API_URL}/v3/mail/send",
            headers={"Authorization": "Bearer invalid-key"},
            json={
                "personalizations": [{"to": [{"email": "test@example.com"}]}],
                "from": {"email": "sender@example.com"},
                "subject": "Test",
                "content": [{"type": "text/plain", "value": "Test"}]
            }
        )
        print(f"   Status: {response.status_code} (expected 401)")

    print("\n✅ SendGrid API tests completed!")


async def test_mailgun_api():
    """Test Mailgun API mock"""
    print("\n=== Testing Mailgun API Mock ===")

    async with httpx.AsyncClient() as client:
        # Health check
        print("\n1. Health check...")
        response = await client.get(f"{MAILGUN_API_URL}/health")
        print(f"   Status: {response.status_code}")

        # Send email
        print("\n2. Send email...")
        response = await client.post(
            f"{MAILGUN_API_URL}/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY.replace("api:", "")),
            data={
                "from": "sender@freeface.com",
                "to": "user@example.com",
                "subject": "Test Email from Mailgun Mock",
                "text": "This is a test email!"
            }
        )
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Message ID: {result['id']}")
        print(f"   Message: {result['message']}")

        # Get events
        print("\n3. Get email events...")
        response = await client.get(
            f"{MAILGUN_API_URL}/{MAILGUN_DOMAIN}/events",
            auth=("api", MAILGUN_API_KEY.replace("api:", ""))
        )
        print(f"   Status: {response.status_code}")
        events = response.json()
        print(f"   Events: {len(events.get('items', []))}")

        # List domains
        print("\n4. List domains...")
        response = await client.get(
            f"{MAILGUN_API_URL}/v3/domains",
            auth=("api", MAILGUN_API_KEY.replace("api:", ""))
        )
        print(f"   Status: {response.status_code}")
        domains = response.json()
        print(f"   Total domains: {domains.get('total_count', 0)}")

    print("\n✅ Mailgun API tests completed!")


async def test_webhook_receiver():
    """Test Webhook Receiver mock"""
    print("\n=== Testing Webhook Receiver Mock ===")

    async with httpx.AsyncClient() as client:
        # Health check
        print("\n1. Health check...")
        response = await client.get(f"{WEBHOOK_URL}/health")
        print(f"   Status: {response.status_code}")

        # Clear history first
        print("\n2. Clear webhook history...")
        response = await client.delete(f"{WEBHOOK_URL}/webhooks/history")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")

        # Send test webhooks
        print("\n3. Send test webhooks...")
        webhooks = [
            {"event": "email.delivered", "email": "user1@example.com"},
            {"event": "email.opened", "email": "user2@example.com"},
            {"event": "email.clicked", "email": "user3@example.com"},
        ]

        for webhook_data in webhooks:
            response = await client.post(
                f"{WEBHOOK_URL}/webhooks/sendgrid",
                json=webhook_data
            )
            print(f"   Sent webhook: {webhook_data['event']} - Status: {response.status_code}")

        # Get webhook history
        print("\n4. Get webhook history...")
        response = await client.get(f"{WEBHOOK_URL}/webhooks/history")
        print(f"   Status: {response.status_code}")
        history = response.json()
        print(f"   Total webhooks: {history['total']}")
        print(f"   Retrieved: {len(history['webhooks'])}")

        # Get webhook stats
        print("\n5. Get webhook statistics...")
        response = await client.get(f"{WEBHOOK_URL}/webhooks/stats")
        print(f"   Status: {response.status_code}")
        stats = response.json()
        print(f"   Total webhooks: {stats['total_webhooks']}")
        print(f"   By method: {stats['by_method']}")

    print("\n✅ Webhook Receiver tests completed!")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Mock Server Integration Tests")
    print("=" * 60)

    try:
        await test_freeface_api()
        await test_sendgrid_api()
        await test_mailgun_api()
        await test_webhook_receiver()

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
