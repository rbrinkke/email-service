# File: /opt/freeface/email/services/freeface_integration.py
# FreeFace Email System - FreeFace Integration
# Integration layer for FreeFace APIs

from models.email_models import EmailPriority

from .email_service import EmailService


class FreeFaceEmailIntegration:
    """Integration layer for FreeFace APIs"""

    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    async def user_registered(self, user_email: str, user_name: str, verification_token: str):
        """Send welcome email when user registers"""
        await self.email_service.send_email(
            recipients=user_email,
            template="user_welcome",
            data={"name": user_name, "verification_link": f"https://freeface.com/verify/{verification_token}"},
            priority=EmailPriority.HIGH,
        )

    async def password_reset_requested(self, user_email: str, reset_token: str):
        """Send password reset email"""
        await self.email_service.send_email(
            recipients=user_email,
            template="password_reset",
            data={"reset_link": f"https://freeface.com/reset/{reset_token}"},
            priority=EmailPriority.HIGH,
        )

    async def group_invitation_sent(self, group_id: str, inviter_name: str, invitee_email: str):
        """Send group invitation"""
        await self.email_service.send_email(
            recipients=invitee_email,
            template="group_invitation",
            data={"inviter": inviter_name, "join_link": f"https://freeface.com/join/{group_id}"},
            priority=EmailPriority.MEDIUM,
        )

    async def new_message_in_group(self, group_id: str, sender_name: str, message_preview: str):
        """Notify group members of new message"""
        await self.email_service.send_email(
            recipients=f"group:{group_id}",
            template="new_message",
            data={
                "sender": sender_name,
                "preview": message_preview,
                "group_link": f"https://freeface.com/group/{group_id}",
            },
            priority=EmailPriority.MEDIUM,
        )
