#!/usr/bin/env python3
"""
Comprehensive test to verify the complete email flow with SMTP/Mailhog
"""

import asyncio
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_email_system():
    """Test the complete email system with SMTP/Mailhog"""
    
    # Import after setting environment to ensure proper config
    from config.email_config import EmailConfig
    from models.email_models import EmailPriority, EmailProvider
    from services.email_service import EmailService
    
    print("=" * 60)
    print("TESTING EMAIL SYSTEM WITH MAILHOG")
    print("=" * 60)
    
    # Initialize configuration
    config = EmailConfig()
    
    # Display configuration
    print("\n1. CONFIGURATION CHECK:")
    print(f"   Redis Host: {config.redis_host}")
    print(f"   Redis Port: {config.redis_port}")
    print(f"   SMTP Configuration:")
    print(f"     - Host: {config.providers['smtp']['host']}")
    print(f"     - Port: {config.providers['smtp']['port']}")
    print(f"     - Use TLS: {config.providers['smtp']['use_tls']}")
    print(f"     - From Email: {config.providers['smtp']['from_email']}")
    
    # Create email service
    print("\n2. INITIALIZING EMAIL SERVICE...")
    email_service = EmailService(config)
    await email_service.initialize()
    print("   ✓ Email service initialized")
    
    # Start workers
    print("\n3. STARTING WORKERS...")
    await email_service.start_workers(worker_count=2)
    print("   ✓ Workers started")
    
    # Send test emails
    print("\n4. SENDING TEST EMAILS:")
    
    test_emails = [
        {
            "name": "Simple Test Email",
            "recipients": "test@example.com",
            "template": "test_email",
            "data": {
                "subject": "Test Email - Simple",
                "message": "This is a simple test email sent via SMTP to Mailhog",
                "name": "Test User"
            },
            "priority": EmailPriority.HIGH
        },
        {
            "name": "Welcome Email",
            "recipients": "newuser@example.com",
            "template": "user_welcome",
            "data": {
                "subject": "Welcome to FreeFace!",
                "name": "New User",
                "verification_link": "https://freeface.com/verify/test123"
            },
            "priority": EmailPriority.HIGH
        },
        {
            "name": "Group Notification",
            "recipients": ["member1@example.com", "member2@example.com"],
            "template": "group_invitation",
            "data": {
                "subject": "You're invited to Saturday Hike!",
                "inviter": "John Doe",
                "group_name": "Saturday Morning Hike",
                "description": "Join us for a refreshing morning hike in the mountains",
                "when": "Saturday, 8:00 AM",
                "where": "Mountain Trail Parking Lot",
                "member_count": 15,
                "join_link": "https://freeface.com/join/hike123"
            },
            "priority": EmailPriority.MEDIUM
        }
    ]
    
    job_ids = []
    for email_config in test_emails:
        print(f"\n   Sending: {email_config['name']}")
        job_id = await email_service.send_email(
            recipients=email_config['recipients'],
            template=email_config['template'],
            data=email_config['data'],
            priority=email_config['priority'],
            provider=EmailProvider.SMTP  # Force SMTP provider
        )
        job_ids.append(job_id)
        print(f"   ✓ Queued with job ID: {job_id}")
    
    # Wait for processing
    print("\n5. WAITING FOR EMAIL PROCESSING...")
    await asyncio.sleep(5)
    
    # Get final stats
    print("\n6. EMAIL SYSTEM STATISTICS:")
    stats = await email_service.get_stats()
    print(f"   Queues:")
    print(f"     - High Priority: {stats.get('queue_high', 0)}")
    print(f"     - Medium Priority: {stats.get('queue_medium', 0)}")
    print(f"     - Low Priority: {stats.get('queue_low', 0)}")
    print(f"   Processing:")
    print(f"     - Sent: {stats.get('sent', 0)}")
    print(f"     - Failed: {stats.get('failed', 0)}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE!")
    print("Check Mailhog Web UI at: http://localhost:8025")
    print("You should see all test emails in the inbox")
    print("=" * 60)
    
    # Shutdown
    await email_service.shutdown()

if __name__ == "__main__":
    # Set environment variables for Mailhog
    os.environ['SMTP_HOST'] = 'localhost'  # Use localhost if running outside Docker
    os.environ['SMTP_PORT'] = '1025'
    os.environ['SMTP_USE_TLS'] = 'false'
    os.environ['SMTP_USERNAME'] = ''
    os.environ['SMTP_PASSWORD'] = ''
    
    asyncio.run(test_email_system())