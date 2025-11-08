#!/usr/bin/env python3
"""
Local Email System Test Script
Tests the email system running locally without Docker
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
import json

# Set environment for local testing
os.environ['REDIS_HOST'] = 'localhost'
os.environ['REDIS_PORT'] = '6379'

from config.email_config import EmailConfig
from models.email_models import EmailPriority, EmailProvider
from services.email_service import EmailService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_email_system():
    """Test the complete email system"""

    print("\n" + "="*60)
    print("📧 FreeFace Email System - Local Test")
    print("="*60 + "\n")

    # Initialize configuration with localhost
    config = EmailConfig(
        redis_host='localhost',
        redis_port=6379
    )

    print("📋 Configuration:")
    print(f"   Redis: {config.redis_host}:{config.redis_port}")
    print(f"   SMTP Host: {config.providers['smtp']['host']}")
    print(f"   SMTP Port: {config.providers['smtp']['port']}")
    print()

    # Create email service
    email_service = EmailService(config)

    try:
        # Initialize service
        print("🔌 Connecting to Redis...")
        await email_service.initialize()
        print("✅ Connected to Redis")
        print()

        # Check initial stats
        print("📊 Initial System Stats:")
        stats = await email_service.get_stats()
        print(f"   High Priority Queue: {stats.get('queue_high', 0)}")
        print(f"   Medium Priority Queue: {stats.get('queue_medium', 0)}")
        print(f"   Low Priority Queue: {stats.get('queue_low', 0)}")
        print(f"   Sent Today: {stats.get('sent', 0)}")
        print(f"   Failed Today: {stats.get('failed', 0)}")
        print()

        # Test 1: Queue a high-priority email
        print("📨 Test 1: Queueing high-priority email...")
        job_id_1 = await email_service.send_email(
            recipients="user@example.com",
            template="test_email",
            data={
                "subject": "Test High Priority Email",
                "message": f"This is a high-priority test sent at {datetime.utcnow().isoformat()}",
                "name": "Test User"
            },
            priority=EmailPriority.HIGH,
            provider=EmailProvider.SMTP
        )
        print(f"✅ Email queued with ID: {job_id_1}")
        print()

        # Test 2: Queue a medium-priority email
        print("📨 Test 2: Queueing medium-priority email...")
        job_id_2 = await email_service.send_email(
            recipients="user2@example.com",
            template="test_email",
            data={
                "subject": "Test Medium Priority Email",
                "message": "This is a medium-priority test",
                "name": "Test User 2"
            },
            priority=EmailPriority.MEDIUM,
            provider=EmailProvider.SMTP
        )
        print(f"✅ Email queued with ID: {job_id_2}")
        print()

        # Test 3: Queue a low-priority email
        print("📨 Test 3: Queueing low-priority email...")
        job_id_3 = await email_service.send_email(
            recipients="user3@example.com",
            template="test_email",
            data={
                "subject": "Test Low Priority Email",
                "message": "This is a low-priority test",
                "name": "Test User 3"
            },
            priority=EmailPriority.LOW,
            provider=EmailProvider.SMTP
        )
        print(f"✅ Email queued with ID: {job_id_3}")
        print()

        # Check updated stats
        print("📊 Updated System Stats:")
        stats = await email_service.get_stats()
        print(f"   High Priority Queue: {stats.get('queue_high', 0)}")
        print(f"   Medium Priority Queue: {stats.get('queue_medium', 0)}")
        print(f"   Low Priority Queue: {stats.get('queue_low', 0)}")
        print()

        # Test 4: Start workers to process emails
        print("👷 Test 4: Starting workers to process emails...")
        print("   (Starting 1 worker for 10 seconds)")
        await email_service.start_workers(worker_count=1)

        # Wait for processing
        for i in range(10, 0, -1):
            print(f"   ⏳ Waiting {i} seconds...", end='\r')
            await asyncio.sleep(1)
        print()

        # Final stats
        print("📊 Final System Stats:")
        stats = await email_service.get_stats()
        print(f"   High Priority Queue: {stats.get('queue_high', 0)}")
        print(f"   Medium Priority Queue: {stats.get('queue_medium', 0)}")
        print(f"   Low Priority Queue: {stats.get('queue_low', 0)}")
        print(f"   Sent Today: {stats.get('sent', 0)}")
        print(f"   Failed Today: {stats.get('failed', 0)}")
        print()

        print("✅ All tests completed successfully!")
        print()
        print("💡 Next steps:")
        print("   1. Start the API: export REDIS_HOST=localhost && python3 api.py")
        print("   2. Start workers: export REDIS_HOST=localhost && python3 worker.py")
        print("   3. Test with curl:")
        print('      curl -X POST http://localhost:8010/send \\')
        print('        -H "Content-Type: application/json" \\')
        print('        -d \'{"recipients": "test@example.com", "template": "test_email", "data": {"subject": "Hello", "message": "World"}}\'')
        print()

        if config.providers['smtp']['host'] == 'localhost':
            print("   ⚠️  Note: SMTP is configured for localhost:1025")
            print("      For email testing, you can:")
            print("      - Run MailHog with Docker: docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog")
            print("      - Or use python's debugging SMTP server: python3 -m smtpd -n -c DebuggingServer localhost:1025")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        await email_service.shutdown()
        print("✅ Shutdown complete")

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(test_email_system())
    sys.exit(exit_code)
