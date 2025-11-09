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
from utils.debug_utils import debug_context, log_provider_operation, log_timing

from .base_provider import EmailProviderBase

logger = logging.getLogger(__name__)


class SMTPProvider(EmailProviderBase):
    """SMTP email provider using aiosmtplib"""

    def __init__(self, config: Dict, redis_client: RedisEmailClient):
        super().__init__("smtp", config, redis_client)

        # Log SMTP configuration (sanitized)
        logger.debug(
            "SMTP Provider initialized: host=%s, port=%s, use_tls=%s",
            config['host'], config['port'], config.get('use_tls', 'true')
        )

        # Set up template environment - use container path
        template_dir = "/opt/email/templates"

        logger.debug("Loading email templates from: %s", template_dir)

        self.template_env = Environment(
            loader=FileSystemLoader(template_dir), autoescape=select_autoescape(["html", "xml"])
        )

        logger.info("SMTP Provider ready: %s:%s", config['host'], config['port'])

    async def _send_email_impl(self, job: EmailJob) -> bool:
        """Send email via SMTP"""

        logger.debug("SMTP: Processing job %s for %s recipient(s)", job.job_id, len(job.to))

        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = self.config["from_email"]
        message["Subject"] = job.data.get("subject", "FreeFace Notification")

        logger.debug(
            "SMTP: Email from=%s, subject='%s'", self.config['from_email'], message['Subject']
        )

        # Render template
        try:
            template_name = f"{job.template}.html"

            logger.debug("SMTP: Attempting to load template '%s'", template_name)

            with log_timing(f"template_render_{job.template}", logger):
                # Try to load the template
                template = self.template_env.get_template(template_name)

                logger.debug("SMTP: Template '%s' loaded successfully", template_name)

                # Render with data
                logger.debug("SMTP: Rendering template with %s data key(s)", len(job.data))

                html_content = template.render(**job.data)

                logger.debug(
                    "SMTP: Template rendered successfully, content length: %s chars", len(html_content)
                )

        except Exception as e:
            # Log the actual error for debugging
            logger.warning(
                "SMTP: Template '%s.html' not found or render error: %s. Using fallback HTML.",
                job.template, e
            )

            # Fallback to simple HTML if template not found
            subject = job.data.get("subject", "FreeFace Notification")
            message_text = job.data.get("message", "Default message")
            html_content = f"<h1>{subject}</h1><p>{message_text}</p>"

            logger.debug("SMTP: Fallback HTML created, length: %s chars", len(html_content))

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        logger.debug("SMTP: MIME message constructed")

        # Send to each recipient
        try:
            # Check if TLS should be used (for Mailhog, we don't need TLS)
            use_tls = self.config.get("use_tls", "true").lower() == "true"

            logger.debug(
                "SMTP: Connecting to %s:%s (TLS=%s)", self.config['host'], self.config['port'], use_tls
            )

            log_provider_operation(
                logger,
                "smtp",
                "connect",
                {
                    "host": self.config["host"],
                    "port": self.config["port"],
                    "use_tls": use_tls,
                    "recipients": len(job.to),
                },
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
                        logger.debug("SMTP: Authenticating as %s", self.config.get('username'))

                        with log_timing("smtp_login", logger):
                            await smtp.login(self.config["username"], self.config["password"])

                        logger.debug("SMTP: Authentication successful")
                    else:
                        logger.debug("SMTP: Skipping authentication (localhost/debug server)")

                    # Send to each recipient
                    sent_count = 0
                    for email in job.to:
                        logger.debug("SMTP: Sending to %s", email)

                        message["To"] = email

                        with log_timing(f"smtp_send_to_{email}", logger):
                            await smtp.send_message(message)

                        sent_count += 1
                        logger.debug(
                            "SMTP: Successfully sent to %s (%s/%s)", email, sent_count, len(job.to)
                        )

                        del message["To"]

                    logger.info(
                        "SMTP: Job %s sent successfully to %s recipient(s)", job.job_id, sent_count
                    )

                    log_provider_operation(
                        logger,
                        "smtp",
                        "send_complete",
                        {
                            "job_id": job.job_id,
                            "recipients_sent": sent_count,
                            "template": job.template,
                        },
                    )

                    return True

        except aiosmtplib.SMTPException as e:
            # SMTP-specific errors
            logger.error("SMTP error for job %s: %s: %s", job.job_id, type(e).__name__, e, exc_info=True)

            log_provider_operation(
                logger,
                "smtp",
                "send_failed",
                {"job_id": job.job_id, "error_type": type(e).__name__, "error": str(e)},
            )

            return False

        except Exception as e:
            # General errors
            logger.error("SMTP error for job %s: %s", job.job_id, e, exc_info=True)

            log_provider_operation(
                logger, "smtp", "send_failed", {"job_id": job.job_id, "error": str(e)}
            )

            return False
