# File: mocks/common/mock_data_generator.py
# Realistic mock data generation using Faker

import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from faker import Faker


class MockDataGenerator:
    """
    Generate realistic mock data for testing

    Uses Faker library to create authentic-looking:
    - User profiles
    - Email addresses
    - Group/community data
    - Timestamps
    - UUIDs

    Usage:
        generator = MockDataGenerator(seed=42)  # Reproducible data
        user = generator.generate_user()
        group = generator.generate_group()
    """

    def __init__(self, seed: Optional[int] = None, locale: str = "en_US"):
        """
        Initialize data generator

        Args:
            seed: Random seed for reproducible data (optional)
            locale: Faker locale for localized data
        """
        self.fake = Faker(locale)
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

    def generate_uuid(self) -> str:
        """Generate a UUID v4"""
        return str(uuid.uuid4())

    def generate_timestamp(
        self,
        days_ago: int = 0,
        hours_ago: int = 0,
        future: bool = False
    ) -> str:
        """
        Generate ISO 8601 timestamp

        Args:
            days_ago: Days in the past (if not future)
            hours_ago: Hours in the past (if not future)
            future: Generate future timestamp

        Returns:
            ISO 8601 formatted timestamp
        """
        now = datetime.utcnow()

        if future:
            delta = timedelta(days=random.randint(1, 30))
            timestamp = now + delta
        else:
            delta = timedelta(days=days_ago, hours=hours_ago)
            timestamp = now - delta

        return timestamp.isoformat() + "Z"

    def generate_user(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict:
        """
        Generate realistic user profile

        Args:
            user_id: Optional specific user ID
            email: Optional specific email

        Returns:
            Dict with user data
        """
        user_id = user_id or self.generate_uuid()
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()

        return {
            "id": user_id,
            "email": email or self.fake.email(),
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
            "username": self.fake.user_name(),
            "phone": self.fake.phone_number(),
            "avatar_url": f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_id}",
            "bio": self.fake.text(max_nb_chars=200),
            "created_at": self.generate_timestamp(days_ago=random.randint(30, 365)),
            "updated_at": self.generate_timestamp(days_ago=random.randint(0, 30)),
            "is_active": random.choice([True, True, True, False]),  # 75% active
            "email_verified": random.choice([True, True, False]),  # 66% verified
        }

    def generate_group(
        self,
        group_id: Optional[str] = None,
        member_count: Optional[int] = None
    ) -> Dict:
        """
        Generate realistic group/community data

        Args:
            group_id: Optional specific group ID
            member_count: Optional specific member count

        Returns:
            Dict with group data
        """
        group_id = group_id or self.generate_uuid()
        member_count = member_count or random.randint(5, 100)

        group_types = ["hiking", "photography", "cooking", "gaming", "reading", "music"]
        group_type = random.choice(group_types)

        return {
            "id": group_id,
            "name": f"{self.fake.catch_phrase()} {group_type.title()} Club",
            "description": self.fake.paragraph(nb_sentences=3),
            "type": group_type,
            "member_count": member_count,
            "is_public": random.choice([True, False]),
            "created_at": self.generate_timestamp(days_ago=random.randint(60, 730)),
            "updated_at": self.generate_timestamp(days_ago=random.randint(0, 60)),
            "avatar_url": f"https://api.dicebear.com/7.x/identicon/svg?seed={group_id}",
            "creator_id": self.generate_uuid(),
            "settings": {
                "allow_invites": True,
                "require_approval": random.choice([True, False]),
                "email_notifications": True,
            }
        }

    def generate_group_member(
        self,
        user_id: Optional[str] = None,
        group_id: Optional[str] = None
    ) -> Dict:
        """
        Generate group membership data

        Args:
            user_id: Optional specific user ID
            group_id: Optional specific group ID

        Returns:
            Dict with membership data
        """
        roles = ["member", "member", "member", "admin", "moderator"]  # Most are members

        return {
            "user_id": user_id or self.generate_uuid(),
            "group_id": group_id or self.generate_uuid(),
            "role": random.choice(roles),
            "joined_at": self.generate_timestamp(days_ago=random.randint(1, 365)),
            "is_active": True,
            "notification_preferences": {
                "email": random.choice([True, False]),
                "push": random.choice([True, False]),
            }
        }

    def generate_email_address(self, domain: str = "example.com") -> str:
        """
        Generate email address with optional custom domain

        Args:
            domain: Email domain

        Returns:
            Email address string
        """
        username = self.fake.user_name()
        return f"{username}@{domain}"

    def generate_batch_users(self, count: int = 10) -> List[Dict]:
        """
        Generate multiple users

        Args:
            count: Number of users to generate

        Returns:
            List of user dicts
        """
        return [self.generate_user() for _ in range(count)]

    def generate_batch_groups(self, count: int = 5) -> List[Dict]:
        """
        Generate multiple groups

        Args:
            count: Number of groups to generate

        Returns:
            List of group dicts
        """
        return [self.generate_group() for _ in range(count)]

    def generate_api_response(
        self,
        data: any,
        success: bool = True,
        message: Optional[str] = None
    ) -> Dict:
        """
        Generate standard API response wrapper

        Args:
            data: Response data
            success: Success status
            message: Optional message

        Returns:
            Standard API response dict
        """
        return {
            "success": success,
            "data": data,
            "message": message,
            "timestamp": self.generate_timestamp(),
        }

    def generate_paginated_response(
        self,
        data: List,
        page: int = 1,
        per_page: int = 20,
        total: Optional[int] = None
    ) -> Dict:
        """
        Generate paginated API response

        Args:
            data: List of items
            page: Current page number
            per_page: Items per page
            total: Total items (defaults to len(data))

        Returns:
            Paginated response dict
        """
        total = total or len(data)
        total_pages = (total + per_page - 1) // per_page

        return {
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "timestamp": self.generate_timestamp(),
        }
