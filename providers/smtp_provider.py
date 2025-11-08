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
from utils.debug_utils import log_timing, debug_context, log_provider_operation

from .base_provider import EmailProviderBase

logger = logging.getLogger(__name__)


class SMTPProvider(EmailProviderBase):
    """SMTP email provider using aiosmtplib"""

    def __init__(self, config: Dict, redis_client: RedisEmailClient):
        super().__init__("smtp", config, redis_client)

        # Log SMTP configuration (sanitized)
        logger.debug(
            f"SMTP Provider initialized: host={config['host']}, "
            f"port={config['port']}, use_tls={config.get('use_tls', 'true')}"
        )

        # Set up template environment - use container path
        template_dir = "/opt/email/templates"

        logger.debug(f"Loading email templates from: {template_dir}")

        self.template_env = Environment(
            loader=FileSystemLoader(template_dir), autoescape=select_autoescape(["html", "xml"])
        )

        logger.info(f"SMTP Provider ready: {config['host']}:{config['port']}")

    async def _send_email_impl(self, job: EmailJob) -> bool:
        """Send email via SMTP"""

        logger.debug(f"SMTP: Processing job {job.job_id} for {len(job.to)} recipient(s)")

        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = self.config["from_email"]
        message["Subject"] = job.data.get("subject", "FreeFace Notification")

        logger.debug(f"SMTP: Email from={self.config['from_email']}, subject='{message['Subject']}'")

        # Render template
        try:
            template_name = f"{job.template}.html"

            logger.debug(f"SMTP: Attempting to load template '{template_name}'")

            with log_timing(f"template_render_{job.template}", logger):
                # Try to load the template
                template = self.template_env.get_template(template_name)

                logger.debug(f"SMTP: Template '{template_name}' loaded successfully")

                # Render with data
                logger.debug(f"SMTP: Rendering template with {len(job.data)} data key(s)")

                html_content = template.render(**job.data)

                logger.debug(f"SMTP: Template rendered successfully, content length: {len(html_content)} chars")

        except Exception as e:
            # Log the actual error for debugging
            logger.warning(
                f"SMTP: Template '{job.template}.html' not found or render error: {e}. "
                f"Using fallback HTML."
            )

            # Fallback to simple HTML if template not found
            subject = job.data.get("subject", "FreeFace Notification")
            message_text = job.data.get("message", "Default message")
            html_content = f"<h1>{subject}</h1><p>{message_text}</p>"

            logger.debug(f"SMTP: Fallback HTML created, length: {len(html_content)} chars")

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        logger.debug("SMTP: MIME message constructed")

        # Send to each recipient
        try:
            # Check if TLS should be used (for Mailhog, we don't need TLS)
            use_tls = self.config.get("use_tls", "true").lower() == "true"

            logger.debug(f"SMTP: Connecting to {self.config['host']}:{self.config['port']} (TLS={use_tls})")

            log_provider_operation(
                logger,
                "smtp",
                "connect",
                {
                    "host": self.config['host'],
                    "port": self.config['port'],
                    "use_tls": use_tls,
                    "recipients": len(job.to)
                }
            )

            with log_timing(f"smtp_send_job_{job.job_id}", logger):
                async with aiosmtplib.SMTP(
                    hostname=self.config["host"], port=int(self.config["port"]), start_tls=use_tls
                ) as smtp:
                    logger.debug("SMTP: Connection established")

                    # Only login if username and password are provided and not empty
                    # Skip login for localhost/debug servers
                    if (
                        self.config.get("username")
                        and self.config.get("password")
                        and self.config["host"] not in ["localhost", "127.0.0.1", "mailhog"]
                    ):
                        logger.debug(f"SMTP: Authenticating as {self.config.get('username')}")

                        with log_timing("smtp_login", logger):
                            await smtp.login(self.config["username"], self.config["password"])

                        logger.debug("SMTP: Authentication successful")
                    else:
                        logger.debug("SMTP: Skipping authentication (localhost/debug server)")

                    # Send to each recipient
                    sent_count = 0
                    for email in job.to:
                        logger.debug(f"SMTP: Sending to {email}")

                        message["To"] = email

                        with log_timing(f"smtp_send_to_{email}", logger):
                            await smtp.send_message(message)

                        sent_count += 1
                        logger.debug(f"SMTP: Successfully sent to {email} ({sent_count}/{len(job.to)})")

                        del message["To"]

                    logger.info(f"SMTP: Job {job.job_id} sent successfully to {sent_count} recipient(s)")

                    log_provider_operation(
                        logger,
                        "smtp",
                        "send_complete",
                        {
                            "job_id": job.job_id,
                            "recipients_sent": sent_count,
                            "template": job.template
                        }
                    )

                    return True

        except aiosmtplib.SMTPException as e:
            # SMTP-specific errors
            logger.error(
                f"SMTP error for job {job.job_id}: {type(e).__name__}: {e}",
                exc_info=True
            )

            log_provider_operation(
                logger,
                "smtp",
                "send_failed",
                {
                    "job_id": job.job_id,
                    "error_type": type(e).__name__,
                    "error": str(e)
                }
            )

            return False

        except Exception as e:
            # General errors
            logger.error(
                f"SMTP error for job {job.job_id}: {e}",
                exc_info=True
            )

            log_provider_operation(
                logger,
                "smtp",
                "send_failed",
                {
                    "job_id": job.job_id,
                    "error": str(e)
                }
            )

            return False
