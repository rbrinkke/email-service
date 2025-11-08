# File: /opt/freeface/email/providers/smtp_provider.py
# FreeFace Email System - SMTP Provider
# SMTP email provider using aiosmtplib

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from models.email_models import EmailJob
from redis_client_lib.redis_client import RedisEmailClient

from .base_provider import EmailProviderBase


class SMTPProvider(EmailProviderBase):
    """SMTP email provider using aiosmtplib"""

    def __init__(self, config: Dict, redis_client: RedisEmailClient):
        super().__init__("smtp", config, redis_client)
        # Set up template environment - use container path
        template_dir = "/opt/email/templates"

        self.template_env = Environment(
            loader=FileSystemLoader(template_dir), autoescape=select_autoescape(["html", "xml"])
        )

    async def _send_email_impl(self, job: EmailJob) -> bool:
        """Send email via SMTP"""

        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = self.config["from_email"]
        message["Subject"] = job.data.get("subject", "FreeFace Notification")

        # Render template
        try:
            # Try to load the template
            template = self.template_env.get_template(f"{job.template}.html")
            html_content = template.render(**job.data)
        except Exception as e:
            # Log the actual error for debugging
            logging.warning(f"Template '{job.template}.html' not found or render error: {e}")
            # Fallback to simple HTML if template not found
            subject = job.data.get("subject", "FreeFace Notification")
            message_text = job.data.get("message", "Default message")
            html_content = f"<h1>{subject}</h1><p>{message_text}</p>"
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        # Send to each recipient
        try:
            # Check if TLS should be used (for Mailhog, we don't need TLS)
            use_tls = self.config.get("use_tls", "true").lower() == "true"

            async with aiosmtplib.SMTP(
                hostname=self.config["host"], port=int(self.config["port"]), start_tls=use_tls
            ) as smtp:
                # Only login if username and password are provided and not empty
                # Skip login for localhost/debug servers
                if (
                    self.config.get("username")
                    and self.config.get("password")
                    and self.config["host"] not in ["localhost", "127.0.0.1", "mailhog"]
                ):
                    await smtp.login(self.config["username"], self.config["password"])

                for email in job.to:
                    message["To"] = email
                    await smtp.send_message(message)
                    del message["To"]

                return True

        except Exception as e:
            logging.error(f"SMTP error: {e}")
            return False
