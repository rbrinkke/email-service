# File: integration_examples.py
# Integration with FreeFace APIs

from typing import Dict

from email_system import EmailConfig, EmailPriority, EmailProvider, EmailService


async def integrate_with_user_api():
    """Example integration with User API (Port 8001)"""

    # Initialize email service
    config = EmailConfig(redis_host="10.10.1.21")
    email_service = EmailService(config)
    await email_service.initialize()

    # User registration handler
    async def on_user_registered(user_data: Dict):
        """Called when a new user registers"""
        await email_service.send_email(
            recipients=user_data["email"],
            template="user_welcome.html",
            data={
                "name": user_data["name"],
                "verification_link": f"https://freeface.com/verify/{user_data['verification_token']}",
            },
            priority=EmailPriority.HIGH,
            provider=EmailProvider.SENDGRID,
        )

    # Password reset handler
    async def on_password_reset_requested(email: str, reset_token: str):
        """Called when user requests password reset"""
        await email_service.send_email(
            recipients=email,
            template="password_reset.html",
            data={"reset_link": f"https://freeface.com/reset/{reset_token}"},
            priority=EmailPriority.HIGH,
        )


async def integrate_with_group_api():
    """Example integration with Group API (Port 8002)"""

    config = EmailConfig(redis_host="10.10.1.21")
    email_service = EmailService(config)
    await email_service.initialize()

    # Group invitation handler
    async def on_group_invitation_sent(invitation_data: Dict):
        """Called when someone is invited to a group"""
        await email_service.send_email(
            recipients=invitation_data["invitee_email"],
            template="group_invitation.html",
            data={
                "inviter": invitation_data["inviter_name"],
                "group_name": invitation_data["group_name"],
                "description": invitation_data.get("description", ""),
                "join_link": f"https://freeface.com/join/{invitation_data['group_id']}",
            },
            priority=EmailPriority.MEDIUM,
        )

    # New member notification
    async def on_member_joined_group(group_id: str, new_member_name: str):
        """Notify group members when someone joins"""
        await email_service.send_email(
            recipients=f"group:{group_id}",
            template="new_message.html",
            data={
                "sender": "FreeFace",
                "group_name": "Your Group",  # Would be fetched from DB
                "preview": f"{new_member_name} joined the group!",
                "group_link": f"https://freeface.com/group/{group_id}",
            },
            priority=EmailPriority.LOW,
        )


async def integrate_with_message_api():
    """Example integration with Message API (Port 8003)"""

    config = EmailConfig(redis_host="10.10.1.21")
    email_service = EmailService(config)
    await email_service.initialize()

    # New message notification
    async def on_message_posted(message_data: Dict):
        """Called when someone posts a message in a group"""

        # Only send emails for groups with notifications enabled
        # and not too frequently (batch digest instead of each message)

        await email_service.send_email(
            recipients=f"group:{message_data['group_id']}",
            template="new_message.html",
            data={
                "sender": message_data["sender_name"],
                "group_name": message_data["group_name"],
                "preview": message_data["message"][:100] + "...",
                "group_link": f"https://freeface.com/group/{message_data['group_id']}",
            },
            priority=EmailPriority.MEDIUM,
        )
