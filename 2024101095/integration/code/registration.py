"""
Registration Module
===================
Handles the registration of new crew members with their name and role.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum


class Role(Enum):
    """Valid roles for crew members."""
    DRIVER = "driver"
    MECHANIC = "mechanic"
    STRATEGIST = "strategist"
    NAVIGATOR = "navigator"
    PIT_CREW = "pit_crew"


@dataclass
class CrewMember:
    """Represents a registered crew member."""
    member_id: int
    name: str
    role: Optional[Role] = None
    skill_level: int = 1  # 1-10 scale
    is_available: bool = True

    def __hash__(self):
        return hash(self.member_id)

    def __eq__(self, other):
        if isinstance(other, CrewMember):
            return self.member_id == other.member_id
        return False


class RegistrationModule:
    """
    Manages crew member registration.

    Provides functionality to register new members, assign IDs,
    and maintain the registry of all crew members.
    """

    def __init__(self):
        self._members: Dict[int, CrewMember] = {}
        self._next_id: int = 1

    def register_member(self, name: str, role: Optional[Role] = None) -> CrewMember:
        """
        Register a new crew member.

        Args:
            name: The name of the crew member
            role: Optional role assignment (can be set later)

        Returns:
            The newly created CrewMember object

        Raises:
            ValueError: If name is empty or whitespace
        """
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")

        member = CrewMember(
            member_id=self._next_id,
            name=name.strip(),
            role=role
        )
        self._members[self._next_id] = member
        self._next_id += 1
        return member

    def get_member(self, member_id: int) -> Optional[CrewMember]:
        """Get a crew member by ID."""
        return self._members.get(member_id)

    def get_member_by_name(self, name: str) -> Optional[CrewMember]:
        """Get a crew member by name (case-insensitive)."""
        name_lower = name.lower()
        for member in self._members.values():
            if member.name.lower() == name_lower:
                return member
        return None

    def get_all_members(self) -> list:
        """Return a list of all registered members."""
        return list(self._members.values())

    def is_registered(self, member_id: int) -> bool:
        """Check if a member ID is registered."""
        return member_id in self._members

    def remove_member(self, member_id: int) -> bool:
        """
        Remove a crew member from the registry.

        Returns:
            True if member was removed, False if not found
        """
        if member_id in self._members:
            del self._members[member_id]
            return True
        return False

    def count(self) -> int:
        """Return the number of registered members."""
        return len(self._members)
