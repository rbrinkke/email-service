# File: email_templates.py
# Email Template Management

import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Dict, Any, List

class EmailTemplateManager:
    """Manages email templates with Jinja2"""
    
    def __init__(self, template_dir: str = "/opt/email/templates"):
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Ensure template directory exists
        os.makedirs(template_dir, exist_ok=True)
        
        # Create default templates
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default email templates"""
        
        templates = {
            'user_welcome.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Welcome to FreeFace!</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .button { 
            display: inline-block; 
            background: #4CAF50; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 10px 0;
        }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Welcome to FreeFace!</h1>
        </div>
        <div class="content">
            <h2>Hi {{ name }}!</h2>
            <p>Welcome to FreeFace, the platform where real connections happen through shared activities.</p>
            
            <p>To get started, please verify your email address by clicking the button below:</p>
            
            <a href="{{ verification_link }}" class="button">✅ Verify Email Address</a>
            
            <p>Once verified, you can:</p>
            <ul>
                <li>🏃‍♀️ Join local activity groups</li>
                <li>👥 Meet like-minded people</li>
                <li>📸 Share moments from your adventures</li>
                <li>🗺️ Discover activities near you</li>
            </ul>
            
            <p>Ready to start your FreeFace journey?</p>
        </div>
        <div class="footer">
            <p>FreeFace - Connect. Explore. Belong.</p>
            <p>If you didn't create an account, you can safely ignore this email.</p>
        </div>
    </div>
</body>
</html>
            """,
            
            'password_reset.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Reset Your FreeFace Password</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #f44336; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .button { 
            display: inline-block; 
            background: #f44336; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 10px 0;
        }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 4px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Password Reset Request</h1>
        </div>
        <div class="content">
            <h2>Reset Your Password</h2>
            <p>We received a request to reset your FreeFace password.</p>
            
            <p>Click the button below to create a new password:</p>
            
            <a href="{{ reset_link }}" class="button">🔑 Reset Password</a>
            
            <div class="warning">
                <strong>⚠️ Security Notice:</strong>
                <ul>
                    <li>This link expires in 1 hour</li>
                    <li>Can only be used once</li>
                    <li>If you didn't request this, ignore this email</li>
                </ul>
            </div>
        </div>
        <div class="footer">
            <p>FreeFace Security Team</p>
            <p>This is an automated message. Please don't reply to this email.</p>
        </div>
    </div>
</body>
</html>
            """,
            
            'group_invitation.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>You're Invited to Join {{ group_name }}!</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2196F3; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .button { 
            display: inline-block; 
            background: #2196F3; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 10px 0;
        }
        .activity-details { background: white; padding: 15px; border-radius: 4px; margin: 15px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 You're Invited!</h1>
        </div>
        <div class="content">
            <h2>{{ inviter }} invited you to join:</h2>
            <div class="activity-details">
                <h3>{{ group_name }}</h3>
                {% if description %}
                <p>{{ description }}</p>
                {% endif %}
                {% if when %}
                <p><strong>📅 When:</strong> {{ when }}</p>
                {% endif %}
                {% if where %}
                <p><strong>📍 Where:</strong> {{ where }}</p>
                {% endif %}
                {% if member_count %}
                <p><strong>👥 Members:</strong> {{ member_count }} people</p>
                {% endif %}
            </div>
            
            <p>Ready to join the fun?</p>
            
            <a href="{{ join_link }}" class="button">🚀 Join Group</a>
            
            <p><small>Not interested? You can safely ignore this invitation.</small></p>
        </div>
        <div class="footer">
            <p>FreeFace - Where activities become friendships</p>
        </div>
    </div>
</body>
</html>
            """,
            
            'new_message.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>New message in {{ group_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #9C27B0; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .message-preview { 
            background: white; 
            padding: 15px; 
            border-left: 4px solid #9C27B0; 
            margin: 15px 0; 
            border-radius: 4px;
        }
        .button { 
            display: inline-block; 
            background: #9C27B0; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 10px 0;
        }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💬 New Message</h1>
        </div>
        <div class="content">
            <h2>{{ sender }} posted in {{ group_name }}:</h2>
            
            <div class="message-preview">
                <p>"{{ preview }}"</p>
            </div>
            
            <a href="{{ group_link }}" class="button">📱 View in Group</a>
            
            <p><small>📧 You're receiving this because you're a member of {{ group_name }}.</small></p>
        </div>
        <div class="footer">
            <p>FreeFace Notifications</p>
            <p><a href="{{ unsubscribe_link }}">Manage notification preferences</a></p>
        </div>
    </div>
</body>
</html>
            """,
            
            'weekly_digest.html': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Your FreeFace Weekly Digest</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #FF5722; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .section { background: white; margin: 15px 0; padding: 15px; border-radius: 4px; }
        .highlight { background: #fff3e0; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .button { 
            display: inline-block; 
            background: #FF5722; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 10px 0;
        }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Your Week on FreeFace</h1>
        </div>
        <div class="content">
            <div class="section">
                <h2>🎯 This Week's Highlights</h2>
                {% for highlight in highlights %}
                <div class="highlight">
                    <h3>{{ highlight.title }}</h3>
                    <p>{{ highlight.description }}</p>
                </div>
                {% endfor %}
            </div>
            
            {% if new_groups %}
            <div class="section">
                <h2>🆕 New Groups Near You</h2>
                {% for group in new_groups %}
                <p><strong>{{ group.name }}</strong> - {{ group.category }}</p>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if active_groups %}
            <div class="section">
                <h2>👥 Your Active Groups</h2>
                {% for group in active_groups %}
                <p><strong>{{ group.name }}</strong> - {{ group.activity_count }} new activities</p>
                {% endfor %}
            </div>
            {% endif %}
            
            <a href="https://freeface.com/discover" class="button">🔍 Discover More</a>
        </div>
        <div class="footer">
            <p>FreeFace Weekly Digest</p>
            <p><a href="{{ unsubscribe_link }}">Unsubscribe</a> | <a href="{{ preferences_link }}">Update Preferences</a></p>
        </div>
    </div>
</body>
</html>
            """
        }
        
        # Write template files
        for filename, content in templates.items():
            filepath = os.path.join(self.template_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content.strip())
    
    def render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Render email template with data"""
        template = self.env.get_template(template_name)
        return template.render(**data)
    
    def get_available_templates(self) -> List[str]:
        """Get list of available templates"""
        return [f for f in os.listdir(self.template_dir) if f.endswith('.html')]
