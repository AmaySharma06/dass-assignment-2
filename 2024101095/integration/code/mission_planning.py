"""
Mission Planning Module
=======================
Assigns missions and verifies required roles are available.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
from datetime import datetime

from .registration import Role, CrewMember
from .crew_management import CrewManagementModule
from .inventory import InventoryModule, Car, CarCondition


class MissionType(Enum):
    """Types of missions."""
    DELIVERY = "delivery"
    RESCUE = "rescue"
    RECON = "reconnaissance"
    GETAWAY = "getaway"
    ESCORT = "escort"
    REPAIR = "repair"


class MissionStatus(Enum):
    """Status of a mission."""
    PLANNING = "planning"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Required roles for each mission type
MISSION_REQUIREMENTS: Dict[MissionType, Set[Role]] = {
    MissionType.DELIVERY: {Role.DRIVER},
    MissionType.RESCUE: {Role.DRIVER, Role.MECHANIC},
    MissionType.RECON: {Role.DRIVER, Role.NAVIGATOR},
    MissionType.GETAWAY: {Role.DRIVER, Role.STRATEGIST},
    MissionType.ESCORT: {Role.DRIVER, Role.NAVIGATOR},
    MissionType.REPAIR: {Role.MECHANIC},
}


@dataclass
class MissionAssignment:
    """Represents a crew member assigned to a mission."""
    member: CrewMember
    role_for_mission: Role


@dataclass
class Mission:
    """Represents a mission."""
    mission_id: int
    name: str
    mission_type: MissionType
    status: MissionStatus = MissionStatus.PLANNING
    assignments: List[MissionAssignment] = field(default_factory=list)
    assigned_car: Optional[Car] = None
    reward: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def get_assigned_roles(self) -> Set[Role]:
        """Get the set of roles currently assigned."""
        return {a.role_for_mission for a in self.assignments}

    def get_required_roles(self) -> Set[Role]:
        """Get the required roles for this mission type."""
        return MISSION_REQUIREMENTS.get(self.mission_type, set())

    def has_all_required_roles(self) -> bool:
        """Check if all required roles are assigned."""
        return self.get_required_roles().issubset(self.get_assigned_roles())


class MissionError(Exception):
    """Base exception for mission errors."""
    pass


class RoleUnavailableError(MissionError):
    """Raised when a required role is not available."""
    pass


class MissionNotFoundError(MissionError):
    """Raised when a mission is not found."""
    pass


class MissionPlanningModule:
    """
    Plans and manages missions.

    Depends on CrewManagementModule and InventoryModule.
    """

    def __init__(self, crew_management: CrewManagementModule,
                 inventory: InventoryModule):
        self._crew = crew_management
        self._inventory = inventory
        self._missions: Dict[int, Mission] = {}
        self._next_mission_id: int = 1

    def create_mission(self, name: str, mission_type: MissionType,
                       reward: float = 0.0) -> Mission:
        """Create a new mission."""
        mission = Mission(
            mission_id=self._next_mission_id,
            name=name,
            mission_type=mission_type,
            reward=reward
        )
        self._missions[self._next_mission_id] = mission
        self._next_mission_id += 1
        return mission

    def get_mission(self, mission_id: int) -> Optional[Mission]:
        """Get a mission by ID."""
        return self._missions.get(mission_id)

    def get_all_missions(self) -> List[Mission]:
        """Get all missions."""
        return list(self._missions.values())

    def get_active_missions(self) -> List[Mission]:
        """Get missions that are in progress."""
        return [
            m for m in self._missions.values()
            if m.status in (MissionStatus.ASSIGNED, MissionStatus.IN_PROGRESS)
        ]

    def check_role_availability(self, mission_type: MissionType) -> Dict[Role, bool]:
        """
        Check if required roles are available for a mission type.

        Returns:
            Dict mapping each required role to availability
        """
        required = MISSION_REQUIREMENTS.get(mission_type, set())
        return {
            role: self._crew.has_available_role(role)
            for role in required
        }

    def can_start_mission(self, mission_type: MissionType) -> bool:
        """Check if all required roles are available."""
        availability = self.check_role_availability(mission_type)
        return all(availability.values())

    def get_missing_roles(self, mission_type: MissionType) -> List[Role]:
        """Get list of required roles that are not available."""
        availability = self.check_role_availability(mission_type)
        return [role for role, available in availability.items() if not available]

    def assign_crew_to_mission(self, mission_id: int,
                               member_id: int, role: Role) -> MissionAssignment:
        """
        Assign a crew member to a mission.

        Raises:
            MissionNotFoundError: If mission not found
            MissionError: If member can't be assigned
        """
        mission = self._missions.get(mission_id)
        if mission is None:
            raise MissionNotFoundError(f"Mission {mission_id} not found")

        if mission.status not in (MissionStatus.PLANNING, MissionStatus.ASSIGNED):
            raise MissionError(
                f"Cannot modify mission in {mission.status.value} status"
            )

        member = self._crew._registration.get_member(member_id)
        if member is None:
            raise MissionError(f"Member {member_id} not found")

        if not member.is_available:
            raise MissionError(f"Member {member.name} is not available")

        if member.role != role:
            raise MissionError(
                f"Member {member.name} has role {member.role}, not {role}"
            )

        # Check if role already assigned
        if role in mission.get_assigned_roles():
            raise MissionError(f"Role {role.value} already assigned")

        assignment = MissionAssignment(member=member, role_for_mission=role)
        mission.assignments.append(assignment)
        member.is_available = False

        if mission.status == MissionStatus.PLANNING:
            mission.status = MissionStatus.ASSIGNED

        return assignment

    def assign_car_to_mission(self, mission_id: int, car_id: int) -> Car:
        """Assign a car to a mission."""
        mission = self._missions.get(mission_id)
        if mission is None:
            raise MissionNotFoundError(f"Mission {mission_id} not found")

        car = self._inventory.get_car(car_id)
        if car is None:
            raise MissionError(f"Car {car_id} not found")

        if not car.is_available:
            raise MissionError(f"Car {car.name} is not available")

        mission.assigned_car = car
        car.is_available = False
        return car

    def start_mission(self, mission_id: int) -> Mission:
        """
        Start a mission, validating all requirements are met.

        Raises:
            MissionError: If requirements not met
        """
        mission = self._missions.get(mission_id)
        if mission is None:
            raise MissionNotFoundError(f"Mission {mission_id} not found")

        if mission.status != MissionStatus.ASSIGNED:
            raise MissionError(
                f"Mission must be in ASSIGNED status to start "
                f"(current: {mission.status.value})"
            )

        # Check all required roles are filled
        required = mission.get_required_roles()
        assigned = mission.get_assigned_roles()
        missing = required - assigned

        if missing:
            raise RoleUnavailableError(
                f"Missing required roles: {[r.value for r in missing]}"
            )

        # Check if car is needed and assigned
        if Role.DRIVER in required and mission.assigned_car is None:
            raise MissionError("Mission requires a car but none assigned")

        mission.status = MissionStatus.IN_PROGRESS
        return mission

    def complete_mission(self, mission_id: int,
                         success: bool = True,
                         car_damaged: bool = False) -> Mission:
        """Mark a mission as complete, releasing resources and crediting reward."""
        mission = self._missions.get(mission_id)
        if mission is None:
            raise MissionNotFoundError(f"Mission {mission_id} not found")

        if mission.status != MissionStatus.IN_PROGRESS:
            raise MissionError("Mission is not in progress")

        # Release crew
        for assignment in mission.assignments:
            assignment.member.is_available = True

        # Handle car
        if mission.assigned_car:
            if car_damaged:
                self._inventory.set_car_condition(
                    mission.assigned_car.car_id, CarCondition.DAMAGED
                )
            mission.assigned_car.is_available = True

        # Handle reward
        if success:
            mission.status = MissionStatus.COMPLETED
            self._inventory.add_funds(mission.reward)
        else:
            mission.status = MissionStatus.FAILED

        mission.completed_at = datetime.now()
        return mission

    def cancel_mission(self, mission_id: int) -> Mission:
        """Cancel a mission and release resources."""
        mission = self._missions.get(mission_id)
        if mission is None:
            raise MissionNotFoundError(f"Mission {mission_id} not found")

        if mission.status in (MissionStatus.COMPLETED, MissionStatus.FAILED):
            raise MissionError("Cannot cancel a finished mission")

        # Release crew
        for assignment in mission.assignments:
            assignment.member.is_available = True

        # Release car
        if mission.assigned_car:
            mission.assigned_car.is_available = True

        mission.status = MissionStatus.CANCELLED
        return mission

    def auto_assign_mission(self, mission_id: int) -> Mission:
        """Automatically assign available crew and car to a mission."""
        mission = self._missions.get(mission_id)
        if mission is None:
            raise MissionNotFoundError(f"Mission {mission_id} not found")

        required_roles = mission.get_required_roles()

        # Check all roles available first
        for role in required_roles:
            if not self._crew.has_available_role(role):
                raise RoleUnavailableError(
                    f"No available crew member with role {role.value}"
                )

        # Auto-assign each role (highest skill level member)
        for role in required_roles:
            available = self._crew.get_available_by_role(role)
            if available:
                best = max(available, key=lambda m: m.skill_level)
                self.assign_crew_to_mission(mission_id, best.member_id, role)

        # Auto-assign car if driver needed
        if Role.DRIVER in required_roles:
            cars = self._inventory.get_race_ready_cars()
            if cars:
                self.assign_car_to_mission(mission_id, cars[0].car_id)

        return mission
