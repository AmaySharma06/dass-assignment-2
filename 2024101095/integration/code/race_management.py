"""
Race Management Module
======================
Creates races and selects appropriate drivers and cars.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime

from .registration import Role, CrewMember
from .crew_management import CrewManagementModule, MemberNotFoundError
from .inventory import InventoryModule, Car, CarCondition, ItemNotFoundError


class RaceStatus(Enum):
    """Status of a race."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RaceType(Enum):
    """Type of race."""
    SPRINT = "sprint"
    DRAG = "drag"
    CIRCUIT = "circuit"
    DRIFT = "drift"


@dataclass
class RaceEntry:
    """Represents a participant in a race."""
    driver: CrewMember
    car: Car
    position: Optional[int] = None
    finished: bool = False
    dnf_reason: Optional[str] = None  # Did Not Finish reason


@dataclass
class Race:
    """Represents a street race."""
    race_id: int
    name: str
    race_type: RaceType
    prize_pool: float
    status: RaceStatus = RaceStatus.SCHEDULED
    entries: List[RaceEntry] = field(default_factory=list)
    scheduled_time: Optional[datetime] = None

    def is_open_for_entry(self) -> bool:
        """Check if the race is still accepting entries."""
        return self.status == RaceStatus.SCHEDULED


class RaceManagementError(Exception):
    """Base exception for race management errors."""
    pass


class InvalidEntryError(RaceManagementError):
    """Raised when a race entry is invalid."""
    pass


class RaceNotFoundError(RaceManagementError):
    """Raised when a race is not found."""
    pass


class RaceManagementModule:
    """
    Manages race creation, entries, and race execution.

    Depends on CrewManagementModule and InventoryModule.
    """

    def __init__(self, crew_management: CrewManagementModule,
                 inventory: InventoryModule):
        self._crew = crew_management
        self._inventory = inventory
        self._races: Dict[int, Race] = {}
        self._next_race_id: int = 1

    def create_race(self, name: str, race_type: RaceType,
                    prize_pool: float,
                    scheduled_time: Optional[datetime] = None) -> Race:
        """Create a new race."""
        if prize_pool < 0:
            raise ValueError("Prize pool cannot be negative")
        race = Race(
            race_id=self._next_race_id,
            name=name,
            race_type=race_type,
            prize_pool=prize_pool,
            scheduled_time=scheduled_time
        )
        self._races[self._next_race_id] = race
        self._next_race_id += 1
        return race

    def get_race(self, race_id: int) -> Optional[Race]:
        """Get a race by ID."""
        return self._races.get(race_id)

    def get_all_races(self) -> List[Race]:
        """Get all races."""
        return list(self._races.values())

    def get_scheduled_races(self) -> List[Race]:
        """Get all scheduled races."""
        return [r for r in self._races.values() if r.status == RaceStatus.SCHEDULED]

    def enter_race(self, race_id: int, driver_id: int, car_id: int) -> RaceEntry:
        """
        Enter a driver and car into a race.

        Raises:
            RaceNotFoundError: If race doesn't exist
            InvalidEntryError: If driver is not a driver or car not available
        """
        race = self._races.get(race_id)
        if race is None:
            raise RaceNotFoundError(f"Race with ID {race_id} not found")

        if not race.is_open_for_entry():
            raise InvalidEntryError(f"Race {race_id} is not accepting entries")

        # Validate driver
        driver = self._crew._registration.get_member(driver_id)
        if driver is None:
            raise InvalidEntryError(f"Driver with ID {driver_id} not found")

        if driver.role != Role.DRIVER:
            raise InvalidEntryError(
                f"Member {driver.name} is not a driver (role: {driver.role})"
            )

        if not driver.is_available:
            raise InvalidEntryError(f"Driver {driver.name} is not available")

        # Validate car
        car = self._inventory.get_car(car_id)
        if car is None:
            raise InvalidEntryError(f"Car with ID {car_id} not found")

        if not car.is_available:
            raise InvalidEntryError(f"Car {car.name} is not available")

        if car.condition not in (CarCondition.PERFECT, CarCondition.GOOD):
            raise InvalidEntryError(
                f"Car {car.name} is not in racing condition ({car.condition.value})"
            )

        # Check if already entered
        for entry in race.entries:
            if entry.driver.member_id == driver_id:
                raise InvalidEntryError(f"Driver {driver.name} already entered")
            if entry.car.car_id == car_id:
                raise InvalidEntryError(f"Car {car.name} already entered")

        # Create entry and mark resources as in use
        entry = RaceEntry(driver=driver, car=car)
        race.entries.append(entry)

        # Mark driver and car as unavailable during race
        driver.is_available = False
        car.is_available = False

        return entry

    def start_race(self, race_id: int) -> Race:
        """
        Start a race.

        Raises:
            RaceNotFoundError: If race doesn't exist
            RaceManagementError: If race can't be started
        """
        race = self._races.get(race_id)
        if race is None:
            raise RaceNotFoundError(f"Race with ID {race_id} not found")

        if race.status != RaceStatus.SCHEDULED:
            raise RaceManagementError(
                f"Race is not scheduled (status: {race.status.value})"
            )

        if not race.entries:
            raise RaceManagementError("Race has no entries")

        race.status = RaceStatus.IN_PROGRESS
        return race

    def cancel_race(self, race_id: int) -> Race:
        """Cancel a race and release all resources."""
        race = self._races.get(race_id)
        if race is None:
            raise RaceNotFoundError(f"Race with ID {race_id} not found")

        if race.status == RaceStatus.COMPLETED:
            raise RaceManagementError("Cannot cancel a completed race")

        # Release resources
        for entry in race.entries:
            entry.driver.is_available = True
            entry.car.is_available = True

        race.status = RaceStatus.CANCELLED
        return race

    def get_suitable_cars_for_race(self, race_type: RaceType) -> List[Car]:
        """Get cars suitable for a specific race type."""
        cars = self._inventory.get_race_ready_cars()
        if race_type in (RaceType.DRAG, RaceType.SPRINT):
            return sorted(cars, key=lambda c: c.horsepower, reverse=True)
        return cars

    def get_available_drivers(self) -> List[CrewMember]:
        """Get all available drivers."""
        return self._crew.get_available_by_role(Role.DRIVER)

    def auto_select_best_entry(self, race_id: int) -> Optional[RaceEntry]:
        """Automatically select and enter the best available driver and car."""
        race = self._races.get(race_id)
        if race is None:
            return None

        best_driver = self._crew.get_best_driver()
        if best_driver is None:
            return None

        suitable_cars = self.get_suitable_cars_for_race(race.race_type)
        if not suitable_cars:
            return None

        best_car = suitable_cars[0]
        return self.enter_race(race_id, best_driver.member_id, best_car.car_id)
