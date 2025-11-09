#!/usr/bin/env python3
"""
Test script to verify SMTP emails are being sent to Mailhog
"""

import asyncio
import logging
from datetime import datetime

from config.email_config import EmailConfig
from models.email_models import EmailPriority, EmailProvider
from services.email_service import EmailService

logging.basicConfig(level=logging.INFO)


async def test_mailhog():
    """Test sending email to Mailhog"""

    # Initialize configuration
    config = EmailConfig()

    # Print SMTP configuration
    print("SMTP Configuration:")
    print(f"  Host: {config.providers['smtp']['host']}")
    print(f"  Port: {config.providers['smtp']['port']}")
    print(f"  Use TLS: {config.providers['smtp']['use_tls']}")
    print()

    # Create email service
    email_service = EmailService(config)
    await email_service.initialize()

    # Start workers
    await email_service.start_workers(worker_count=1)

    print("Sending test email to Mailhog...")

    # Send test email explicitly using SMTP provider
    job_id = await email_service.send_email(
        recipients="test@example.com",
        template="test_email",
        data={
            "subject": "Test Email to Mailhog",
            "message": f"This is a test email sent at {datetime.utcnow().isoformat()}",
            "name": "Test User",
        },
        priority=EmailPriority.HIGH,
        provider=EmailProvider.SMTP,  # Explicitly use SMTP
    )

    print(f"Email queued with job ID: {job_id}")
    print("Waiting for email to be processed...")

    # Give workers time to process
    await asyncio.sleep(5)

    # Get stats
    stats = await email_service.get_stats()
    print(f"Email system stats: {stats}")

    print("\nCheck Mailhog web UI at http://localhost:8025 to see the email")

    # Shutdown
    await email_service.shutdown()


if __name__ == "__main__":
    asyncio.run(test_mailhog())
