#!/usr/bin/env python3
# File: mocks/freeface_api/freeface_api_mock.py
# FreeFace Platform API Mock Server

import sys
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, HTTPException, Query

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base_mock import BaseMockServer
from common.error_simulator import ErrorSimulator
from common.middleware import add_mock_middleware
from common.mock_data_generator import MockDataGenerator
from freeface_api.models import (
    GroupDetails,
    GroupMemberWithProfile,
    PaginatedGroupMembersResponse,
    PaginationMeta,
    UserProfile,
    UserResolveRequest,
    UserResolveResponse,
)


class FreeFaceAPIMock(BaseMockServer):
    """
    Mock server for FreeFace Platform API

    Simulates user management and group/community endpoints
    that the email service needs to integrate with.

    Endpoints:
    - GET  /api/v1/users/{user_id}              - Get user profile
    - POST /api/v1/users/resolve                - Resolve multiple users
    - GET  /api/v1/groups/{group_id}            - Get group details
    - GET  /api/v1/groups/{group_id}/members    - List group members
    - GET  /health                               - Health check

    Features:
    - Realistic seed data with 50 users and 10 groups
    - Pagination support
    - Error simulation via ?simulate_error=404
    - Response delay via ?delay_ms=1000
    - Full OpenAPI documentation at /docs
    """

    def __init__(self):
        """Initialize FreeFace API mock server"""
        super().__init__(
            title="FreeFace Platform API Mock",
            description="Mock server for FreeFace user and group management APIs",
            version="1.0.0"
        )

        # Initialize utilities
        self.data_generator = MockDataGenerator(seed=42)  # Reproducible data
        self.error_simulator = ErrorSimulator()

        # In-memory storage
        self.users: Dict[str, UserProfile] = {}
        self.groups: Dict[str, GroupDetails] = {}
        self.group_members: Dict[str, List[str]] = {}  # group_id -> [user_ids]

        # Generate seed data
        self._generate_seed_data()

        # Add middleware
        add_mock_middleware(self.app, enable_logging=True, enable_delay=True)

        # Setup routes
        self._setup_routes()

        self.logger.info(
            "Seed data loaded: %d users, %d groups",
            len(self.users),
            len(self.groups)
        )

    def _generate_seed_data(self):
        """Generate realistic seed data"""
        # Generate 50 users
        for _ in range(50):
            user_data = self.data_generator.generate_user()
            user = UserProfile(**user_data)
            self.users[user.id] = user

        # Generate 10 groups
        for _ in range(10):
            group_data = self.data_generator.generate_group()
            group = GroupDetails(**group_data)
            self.groups[group.id] = group

            # Assign random users to each group
            user_ids = list(self.users.keys())
            import random
            random.seed(42)
            member_count = random.randint(5, 20)
            members = random.sample(user_ids, min(member_count, len(user_ids)))
            self.group_members[group.id] = members

            # Update member count
            group.member_count = len(members)

        self.logger.debug("Generated seed data: users=%d, groups=%d", len(self.users), len(self.groups))

    def _setup_routes(self):
        """Setup API routes"""

        @self.app.get("/api/v1/users/{user_id}", response_model=UserProfile)
        async def get_user(
            user_id: str,
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            Get user profile by ID

            - **user_id**: User UUID

            **Error Simulation:**
            - ?simulate_error=404 - Simulate user not found
            - ?simulate_error=500 - Simulate server error
            """
            self.logger.info("Get user: %s", user_id)

            if user_id not in self.users:
                self.error_simulator.raise_not_found("user", user_id)

            return self.users[user_id]

        @self.app.post("/api/v1/users/resolve", response_model=UserResolveResponse)
        async def resolve_users(
            request: UserResolveRequest,
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            Resolve multiple users by IDs

            Returns profiles for found users and list of not found IDs.

            **Request Body:**
            ```json
            {
                "user_ids": ["uuid1", "uuid2", "uuid3"]
            }
            ```

            **Error Simulation:**
            - ?simulate_error=400 - Simulate bad request
            - ?simulate_error=500 - Simulate server error
            """
            self.logger.info("Resolve users: %d IDs", len(request.user_ids))

            found_users = []
            not_found = []

            for user_id in request.user_ids:
                if user_id in self.users:
                    found_users.append(self.users[user_id])
                else:
                    not_found.append(user_id)

            return UserResolveResponse(
                users=found_users,
                not_found=not_found
            )

        @self.app.get("/api/v1/groups/{group_id}", response_model=GroupDetails)
        async def get_group(
            group_id: str,
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            Get group details by ID

            - **group_id**: Group UUID

            **Error Simulation:**
            - ?simulate_error=404 - Simulate group not found
            """
            self.logger.info("Get group: %s", group_id)

            if group_id not in self.groups:
                self.error_simulator.raise_not_found("group", group_id)

            return self.groups[group_id]

        @self.app.get(
            "/api/v1/groups/{group_id}/members",
            response_model=PaginatedGroupMembersResponse
        )
        async def list_group_members(
            group_id: str,
            page: int = Query(1, ge=1, description="Page number"),
            per_page: int = Query(20, ge=1, le=100, description="Items per page"),
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            List group members with pagination

            Returns member details with full user profiles.

            **Query Parameters:**
            - page: Page number (default: 1)
            - per_page: Items per page (default: 20, max: 100)

            **Error Simulation:**
            - ?simulate_error=404 - Simulate group not found
            """
            self.logger.info("List group members: %s (page=%d, per_page=%d)", group_id, page, per_page)

            if group_id not in self.groups:
                self.error_simulator.raise_not_found("group", group_id)

            # Get member user IDs
            member_ids = self.group_members.get(group_id, [])

            # Calculate pagination
            total = len(member_ids)
            total_pages = (total + per_page - 1) // per_page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page

            # Get paginated member IDs
            page_member_ids = member_ids[start_idx:end_idx]

            # Build member objects with profiles
            members_with_profiles = []
            for user_id in page_member_ids:
                if user_id in self.users:
                    member_data = self.data_generator.generate_group_member(
                        user_id=user_id,
                        group_id=group_id
                    )
                    member = GroupMemberWithProfile(
                        **member_data,
                        profile=self.users[user_id]
                    )
                    members_with_profiles.append(member)

            # Build pagination metadata
            pagination = PaginationMeta(
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )

            return PaginatedGroupMembersResponse(
                data=members_with_profiles,
                pagination=pagination,
                timestamp=self.data_generator.generate_timestamp()
            )

        @self.app.get("/api/v1/users")
        async def list_users(
            page: int = Query(1, ge=1, description="Page number"),
            per_page: int = Query(20, ge=1, le=100, description="Items per page"),
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            List all users with pagination

            **Query Parameters:**
            - page: Page number (default: 1)
            - per_page: Items per page (default: 20, max: 100)
            """
            self.logger.info("List users (page=%d, per_page=%d)", page, per_page)

            all_users = list(self.users.values())
            total = len(all_users)
            total_pages = (total + per_page - 1) // per_page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page

            page_users = all_users[start_idx:end_idx]

            pagination = PaginationMeta(
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )

            return {
                "data": page_users,
                "pagination": pagination,
                "timestamp": self.data_generator.generate_timestamp()
            }

        @self.app.get("/api/v1/groups")
        async def list_groups(
            page: int = Query(1, ge=1, description="Page number"),
            per_page: int = Query(20, ge=1, le=100, description="Items per page"),
            _error_check=Depends(self.check_error_simulation)
        ):
            """
            List all groups with pagination

            **Query Parameters:**
            - page: Page number (default: 1)
            - per_page: Items per page (default: 20, max: 100)
            """
            self.logger.info("List groups (page=%d, per_page=%d)", page, per_page)

            all_groups = list(self.groups.values())
            total = len(all_groups)
            total_pages = (total + per_page - 1) // per_page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page

            page_groups = all_groups[start_idx:end_idx]

            pagination = PaginationMeta(
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )

            return {
                "data": page_groups,
                "pagination": pagination,
                "timestamp": self.data_generator.generate_timestamp()
            }


def main():
    """Run the mock server"""
    import os

    mock = FreeFaceAPIMock()

    # Allow port override via environment
    port = int(os.getenv("MOCK_PORT", "8001"))

    mock.run(port=port)


if __name__ == "__main__":
    main()
