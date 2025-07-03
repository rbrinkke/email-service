# File: /opt/freeface/email/config/email_config.py
# FreeFace Email System - Configuration Module
# Contains all configuration classes and settings for the email system

from dataclasses import dataclass
from typing import Dict, Optional
import os

@dataclass
class EmailConfig:
    """Complete email system configuration"""
    # Redis Configuration
    redis_host: str = "redis-email"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Rate Limiting (Token Bucket)
    rate_limits: Dict[str, Dict[str, int]] = None
    
    # Provider Configurations
    providers: Dict[str, Dict[str, str]] = None
    
    # Worker Configuration
    worker_concurrency: int = 100
    batch_size: int = 50
    retry_attempts: int = 3
    dead_letter_ttl: int = 86400 * 7  # 7 days
    
    # Templates
    template_directory: str = "/opt/email/templates"
    
    def __post_init__(self):
        if self.rate_limits is None:
            self.rate_limits = {
                "sendgrid": {"bucket_size": 500, "refill_rate": 100},
                "mailgun": {"bucket_size": 1000, "refill_rate": 200},
                "aws_ses": {"bucket_size": 200, "refill_rate": 50},
                "smtp": {"bucket_size": 100, "refill_rate": 20}
            }
        
        if self.providers is None:
            self.providers = {
                "sendgrid": {
                    "api_key": "SG.xxx",
                    "from_email": "noreply@freeface.com",
                    "api_url": "https://api.sendgrid.com/v3/mail/send"
                },
                "mailgun": {
                    "api_key": "key-xxx",
                    "domain": "mg.freeface.com",
                    "from_email": "noreply@freeface.com",
                    "api_url": "https://api.mailgun.net/v3"
                },
                "smtp": {
                    "host": os.getenv('SMTP_HOST', 'mailhog'),
                    "port": os.getenv('SMTP_PORT', '1025'),
                    "username": os.getenv('SMTP_USERNAME', 'test@example.com'),
                    "password": os.getenv('SMTP_PASSWORD', 'test_smtp_password'),
                    "from_email": os.getenv('SMTP_FROM_EMAIL', 'noreply@freeface.com'),
                    "use_tls": os.getenv('SMTP_USE_TLS', 'false')
                }
            }
