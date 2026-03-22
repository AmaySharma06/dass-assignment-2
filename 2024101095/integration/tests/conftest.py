"""
Shared pytest fixtures for StreetRace Manager integration tests.
"""
import sys
from pathlib import Path

import pytest

# Ensure the repo root (dass-assignment-2/) is on the path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.code import (
    Role, RegistrationModule,
    CrewManagementModule,
    InventoryModule,
    RaceManagementModule,
    ResultsModule,
    MissionPlanningModule,
    LeaderboardModule,
    NotificationsModule,
)
from integration.code.race_management import RaceType


@pytest.fixture
def registration():
    return RegistrationModule()


@pytest.fixture
def crew_management(registration):
    return CrewManagementModule(registration)


@pytest.fixture
def inventory():
    return InventoryModule(initial_balance=10_000.0)


@pytest.fixture
def race_management(crew_management, inventory):
    return RaceManagementModule(crew_management, inventory)


@pytest.fixture
def results(race_management, inventory):
    return ResultsModule(race_management, inventory)


@pytest.fixture
def mission_planning(crew_management, inventory):
    return MissionPlanningModule(crew_management, inventory)


@pytest.fixture
def leaderboard(results):
    return LeaderboardModule(results)


@pytest.fixture
def notifications():
    return NotificationsModule()


@pytest.fixture
def full_system(registration, crew_management, inventory,
                race_management, results, mission_planning,
                leaderboard, notifications):
    return {
        'registration': registration,
        'crew': crew_management,
        'inventory': inventory,
        'race': race_management,
        'results': results,
        'mission': mission_planning,
        'leaderboard': leaderboard,
        'notifications': notifications,
    }
