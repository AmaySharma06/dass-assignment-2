"""
Crew Management Module
======================
Manages roles, skill levels, and assignments for crew members.
"""
from typing import Dict, List, Optional
from .registration import RegistrationModule, CrewMember, Role


class CrewManagementError(Exception):
    """Base exception for crew management errors."""
    pass


class MemberNotFoundError(CrewManagementError):
    """Raised when a member is not found."""
    pass


class InvalidRoleError(CrewManagementError):
    """Raised when an invalid role operation is attempted."""
    pass


class CrewManagementModule:
    """
    Manages crew roles, skill levels, and team assignments.

    Depends on RegistrationModule for member lookup.
    """

    def __init__(self, registration: RegistrationModule):
        self._registration = registration
        self._teams: Dict[str, List[int]] = {}  # team_name -> member_ids

    def assign_role(self, member_id: int, role: Role) -> CrewMember:
        """
        Assign a role to a crew member.

        Raises:
            MemberNotFoundError: If member is not registered
        """
        member = self._registration.get_member(member_id)
        if member is None:
            raise MemberNotFoundError(f"Member with ID {member_id} not found")
        member.role = role
        return member

    def update_skill_level(self, member_id: int, skill_level: int) -> CrewMember:
        """
        Update a crew member's skill level (1-10).

        Raises:
            MemberNotFoundError: If member is not registered
            ValueError: If skill level is out of range
        """
        if not 1 <= skill_level <= 10:
            raise ValueError("Skill level must be between 1 and 10")
        member = self._registration.get_member(member_id)
        if member is None:
            raise MemberNotFoundError(f"Member with ID {member_id} not found")
        member.skill_level = skill_level
        return member

    def set_availability(self, member_id: int, available: bool) -> CrewMember:
        """
        Set a crew member's availability status.

        Raises:
            MemberNotFoundError: If member is not registered
        """
        member = self._registration.get_member(member_id)
        if member is None:
            raise MemberNotFoundError(f"Member with ID {member_id} not found")
        member.is_available = available
        return member

    def get_members_by_role(self, role: Role) -> List[CrewMember]:
        """Get all members with a specific role."""
        return [
            m for m in self._registration.get_all_members()
            if m.role == role
        ]

    def get_available_members(self) -> List[CrewMember]:
        """Get all available crew members."""
        return [m for m in self._registration.get_all_members() if m.is_available]

    def get_available_by_role(self, role: Role) -> List[CrewMember]:
        """Get all available members with a specific role."""
        return [
            m for m in self._registration.get_all_members()
            if m.role == role and m.is_available
        ]

    def has_available_role(self, role: Role) -> bool:
        """Check if there's at least one available member with the given role."""
        return len(self.get_available_by_role(role)) > 0

    def create_team(self, team_name: str, member_ids: List[int]) -> List[CrewMember]:
        """
        Create a named team with specified members.

        Raises:
            MemberNotFoundError: If any member is not registered
        """
        members = []
        for mid in member_ids:
            member = self._registration.get_member(mid)
            if member is None:
                raise MemberNotFoundError(f"Member with ID {mid} not found")
            members.append(member)
        self._teams[team_name] = member_ids
        return members

    def get_team(self, team_name: str) -> Optional[List[CrewMember]]:
        """Get all members in a team."""
        if team_name not in self._teams:
            return None
        return [
            self._registration.get_member(mid)
            for mid in self._teams[team_name]
            if self._registration.get_member(mid) is not None
        ]

    def get_best_driver(self) -> Optional[CrewMember]:
        """Get the available driver with highest skill level."""
        drivers = self.get_available_by_role(Role.DRIVER)
        if not drivers:
            return None
        return max(drivers, key=lambda m: m.skill_level)
