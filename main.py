# File: /opt/freeface/email/main.py
# FreeFace Email System - Main Application Entry Point
# Main application entry point and example usage

import asyncio
import logging
from datetime import datetime, timedelta

from config.email_config import EmailConfig
from models.email_models import EmailPriority
from services.email_service import EmailService
from services.freeface_integration import FreeFaceEmailIntegration

async def main():
    """Main application entry point"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/opt/freeface/email/logs/email.log'),
            logging.StreamHandler()
        ]
    )
    
    # Initialize configuration
    config = EmailConfig()
    
    # Create email service
    email_service = EmailService(config)
    await email_service.initialize()
    
    # Start workers
    await email_service.start_workers(worker_count=3)
    
    # Create integration layer
    integration = FreeFaceEmailIntegration(email_service)
    
    # Example usage
    logging.info("FreeFace Email System started - sending test emails")
    
    # Example: Send welcome email
    job_id = await email_service.send_email(
        recipients="user@example.com",
        template="welcome",
        data={
            "name": "John Doe",
            "verification_link": "https://freeface.com/verify/abc123"
        },
        priority=EmailPriority.HIGH
    )
    
    # Example: Send group invitation
    job_id = await email_service.send_email(
        recipients="group:hiking_123",
        template="group_invitation",
        data={
            "inviter": "Sarah",
            "group_name": "Saturday Morning Hike",
            "join_link": "https://freeface.com/join/hiking_123"
        },
        priority=EmailPriority.MEDIUM
    )
    
    # Example: Schedule newsletter
    scheduled_time = datetime.utcnow() + timedelta(hours=1)
    job_id = await email_service.send_email(
        recipients="group:newsletter_subscribers",
        template="weekly_newsletter",
        data={
            "week": "2024-01-20",
            "highlights": ["New groups in Amsterdam", "Feature updates"]
        },
        priority=EmailPriority.LOW,
        scheduled_at=scheduled_time
    )
    
    # Monitor statistics
    try:
        while True:
            stats = await email_service.get_stats()
            logging.info(f"Email system stats: {stats}")
            await asyncio.sleep(30)
    except KeyboardInterrupt:
        logging.info("Shutting down email system...")
        await email_service.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
