# File: mocks/freeface_api/models.py
# Pydantic models for FreeFace API

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    """User profile model"""
    id: str = Field(..., description="Unique user ID (UUID)")
    email: EmailStr = Field(..., description="User email address")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    full_name: str = Field(..., description="User full name")
    username: str = Field(..., description="Unique username")
    phone: Optional[str] = Field(None, description="Phone number")
    avatar_url: str = Field(..., description="Avatar image URL")
    bio: Optional[str] = Field(None, description="User bio/description")
    created_at: str = Field(..., description="Account creation timestamp (ISO 8601)")
    updated_at: str = Field(..., description="Last update timestamp (ISO 8601)")
    is_active: bool = Field(True, description="Account active status")
    email_verified: bool = Field(False, description="Email verification status")


class GroupSettings(BaseModel):
    """Group settings model"""
    allow_invites: bool = True
    require_approval: bool = False
    email_notifications: bool = True


class GroupDetails(BaseModel):
    """Group/community details model"""
    id: str = Field(..., description="Unique group ID (UUID)")
    name: str = Field(..., description="Group name")
    description: str = Field(..., description="Group description")
    type: str = Field(..., description="Group type/category")
    member_count: int = Field(..., description="Number of members")
    is_public: bool = Field(True, description="Public visibility")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    updated_at: str = Field(..., description="Last update timestamp (ISO 8601)")
    avatar_url: str = Field(..., description="Group avatar URL")
    creator_id: str = Field(..., description="Creator user ID")
    settings: GroupSettings = Field(..., description="Group settings")


class GroupMember(BaseModel):
    """Group member model"""
    user_id: str = Field(..., description="User ID")
    group_id: str = Field(..., description="Group ID")
    role: str = Field(..., description="Member role (member, admin, moderator)")
    joined_at: str = Field(..., description="Join timestamp (ISO 8601)")
    is_active: bool = Field(True, description="Active membership status")
    notification_preferences: Dict[str, bool] = Field(
        default_factory=dict,
        description="Notification preferences"
    )


class GroupMemberWithProfile(GroupMember):
    """Group member with full user profile"""
    profile: UserProfile = Field(..., description="User profile")


class UserResolveRequest(BaseModel):
    """Request to resolve multiple users"""
    user_ids: List[str] = Field(..., description="List of user IDs to resolve")


class UserResolveResponse(BaseModel):
    """Response with resolved users"""
    users: List[UserProfile] = Field(..., description="Resolved user profiles")
    not_found: List[str] = Field(default_factory=list, description="User IDs not found")


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(1, description="Current page number")
    per_page: int = Field(20, description="Items per page")
    total: int = Field(..., description="Total items")
    total_pages: int = Field(..., description="Total pages")
    has_next: bool = Field(False, description="Has next page")
    has_prev: bool = Field(False, description="Has previous page")


class PaginatedGroupMembersResponse(BaseModel):
    """Paginated group members response"""
    data: List[GroupMemberWithProfile] = Field(..., description="Group members")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    timestamp: str = Field(..., description="Response timestamp")


class ApiResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = Field(True, description="Success status")
    data: Optional[any] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Optional message")
    timestamp: str = Field(..., description="Response timestamp")
