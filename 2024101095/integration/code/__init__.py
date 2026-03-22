"""
StreetRace Manager – Code Package
"""

from .registration import Role, CrewMember, RegistrationModule
from .crew_management import (
    CrewManagementModule, CrewManagementError,
    MemberNotFoundError, InvalidRoleError
)
from .inventory import (
    CarCondition, Car, SparePart, Tool,
    InsufficientFundsError, ItemNotFoundError,
    InventoryModule
)
from .race_management import (
    RaceStatus, Race, RaceEntry, RaceManagementError,
    InvalidEntryError, RaceNotFoundError, RaceManagementModule
)
from .results import (
    RaceOutcome, RaceResult, DriverStats, ResultsError, ResultsModule
)
from .mission_planning import (
    MissionType, MissionStatus, Mission, MissionAssignment,
    MissionError, RoleUnavailableError, MissionNotFoundError,
    MissionPlanningModule, MISSION_REQUIREMENTS
)
from .leaderboard import (
    LeaderboardType, TimePeriod, LeaderboardEntry, CrewPerformance,
    Achievement, LeaderboardModule, ACHIEVEMENTS
)
from .notifications import (
    NotificationType, NotificationCategory, NotificationPriority,
    Notification, NotificationPreference, NotificationsModule
)

__all__ = [
    'Role', 'CrewMember', 'RegistrationModule',
    'CrewManagementModule', 'CrewManagementError',
    'MemberNotFoundError', 'InvalidRoleError',
    'CarCondition', 'Car', 'SparePart', 'Tool',
    'InsufficientFundsError', 'ItemNotFoundError', 'InventoryModule',
    'RaceStatus', 'Race', 'RaceEntry', 'RaceManagementError',
    'InvalidEntryError', 'RaceNotFoundError', 'RaceManagementModule',
    'RaceOutcome', 'RaceResult', 'DriverStats', 'ResultsError', 'ResultsModule',
    'MissionType', 'MissionStatus', 'Mission', 'MissionAssignment',
    'MissionError', 'RoleUnavailableError', 'MissionNotFoundError',
    'MissionPlanningModule', 'MISSION_REQUIREMENTS',
    'LeaderboardType', 'TimePeriod', 'LeaderboardEntry', 'CrewPerformance',
    'Achievement', 'LeaderboardModule', 'ACHIEVEMENTS',
    'NotificationType', 'NotificationCategory', 'NotificationPriority',
    'Notification', 'NotificationPreference', 'NotificationsModule',
]
