# File: email_system.py
# Complete FreeFace Email System - Core Module
# This file contains all the core email system classes and functionality

# Import all the classes and functions from the original email system
# This acts as a bridge to maintain compatibility with the Docker services

# Re-export all the main classes for the containerized services
from config.email_config import EmailConfig
from models.email_models import EmailJob, EmailPriority, EmailProvider, EmailStatus
from redis.redis_client import RedisEmailClient
from services.email_service import EmailService
from services.freeface_integration import FreeFaceEmailIntegration
from workers.email_worker import EmailWorker
from workers.circuit_breaker import CircuitBreaker
from providers.base_provider import EmailProviderBase
from providers.sendgrid_provider import SendGridProvider
from providers.smtp_provider import SMTPProvider

# Export all classes for easy import
__all__ = [
    'EmailConfig',
    'EmailJob',
    'EmailPriority', 
    'EmailProvider',
    'EmailStatus',
    'RedisEmailClient',
    'EmailService',
    'FreeFaceEmailIntegration',
    'EmailWorker',
    'CircuitBreaker',
    'EmailProviderBase',
    'SendGridProvider',
    'SMTPProvider'
]
