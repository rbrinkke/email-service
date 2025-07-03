# File: /opt/freeface/email/providers/smtp_provider.py
# FreeFace Email System - SMTP Provider
# SMTP email provider using aiosmtplib

import logging
from typing import Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib
from jinja2 import Environment, DictLoader, select_autoescape

from .base_provider import EmailProviderBase
from ..models.email_models import EmailJob
from ..redis.redis_client import RedisEmailClient

class SMTPProvider(EmailProviderBase):
    """SMTP email provider using aiosmtplib"""
    
    def __init__(self, config: Dict, redis_client: RedisEmailClient):
        super().__init__("smtp", config, redis_client)
        self.template_env = Environment(
            loader=DictLoader({}),  # Templates loaded separately
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    async def _send_email_impl(self, job: EmailJob) -> bool:
        """Send email via SMTP"""
        
        # Create message
        message = MIMEMultipart('alternative')
        message['From'] = self.config['from_email']
        message['Subject'] = job.data.get('subject', 'FreeFace Notification')
        
        # Render template (simplified - would use actual template engine)
        html_content = f"<h1>FreeFace</h1><p>{job.data.get('message', 'Default message')}</p>"
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)
        
        # Send to each recipient
        try:
            async with aiosmtplib.SMTP(
                hostname=self.config['host'],
                port=int(self.config['port']),
                start_tls=True
            ) as smtp:
                await smtp.login(self.config['username'], self.config['password'])
                
                for email in job.to:
                    message['To'] = email
                    await smtp.send_message(message)
                    del message['To']
                
                return True
                
        except Exception as e:
            logging.error(f"SMTP error: {e}")
            return False
