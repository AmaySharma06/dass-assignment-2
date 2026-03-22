"""
Results Module
==============
Records race outcomes, updates rankings, and handles prize money.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .registration import CrewMember
from .inventory import InventoryModule, CarCondition
from .race_management import (
    RaceManagementModule, Race, RaceStatus, RaceEntry, RaceNotFoundError
)


@dataclass
class RaceResult:
    """Detailed result for a single race entry."""
    entry: RaceEntry
    position: int
    prize_won: float
    time_seconds: Optional[float] = None


@dataclass
class RaceOutcome:
    """Complete outcome of a race."""
    race: Race
    results: List[RaceResult]
    total_prize_distributed: float
    completed_at: datetime = field(default_factory=datetime.now)


@dataclass
class DriverStats:
    """Cumulative statistics for a driver."""
    driver_id: int
    driver_name: str
    races_entered: int = 0
    races_won: int = 0
    podium_finishes: int = 0  # Top 3
    total_earnings: float = 0.0
    dnf_count: int = 0

    @property
    def win_rate(self) -> float:
        """Calculate win rate as percentage."""
        if self.races_entered == 0:
            return 0.0
        return (self.races_won / self.races_entered) * 100


class ResultsError(Exception):
    """Base exception for results module errors."""
    pass


class ResultsModule:
    """
    Records race outcomes and manages rankings.

    Depends on RaceManagementModule and InventoryModule.
    """

    # Prize distribution percentages by position
    PRIZE_DISTRIBUTION = {
        1: 0.50,  # Winner gets 50%
        2: 0.30,  # Second place 30%
        3: 0.15,  # Third place 15%
    }
    # Remaining 5% goes to all other finishers equally

    def __init__(self, race_management: RaceManagementModule,
                 inventory: InventoryModule):
        self._race_mgmt = race_management
        self._inventory = inventory
        self._outcomes: Dict[int, RaceOutcome] = {}   # race_id -> outcome
        self._driver_stats: Dict[int, DriverStats] = {}  # driver_id -> stats

    def record_race_results(
        self,
        race_id: int,
        finishing_order: List[int],          # driver_ids in finishing order
        dnf_drivers: Optional[Dict[int, str]] = None,  # driver_id -> reason
        damage_drivers: Optional[List[int]] = None     # drivers whose cars got damaged
    ) -> RaceOutcome:
        """
        Record the results of a completed race.

        Args:
            race_id: The race that completed
            finishing_order: Driver IDs in order of finish
            dnf_drivers: Map of driver IDs to DNF reasons
            damage_drivers: List of driver IDs whose cars were damaged

        Returns:
            The RaceOutcome

        Raises:
            ResultsError: If race can't be finalized
        """
        race = self._race_mgmt.get_race(race_id)
        if race is None:
            raise RaceNotFoundError(f"Race with ID {race_id} not found")

        if race.status != RaceStatus.IN_PROGRESS:
            raise ResultsError(
                f"Race is not in progress (status: {race.status.value})"
            )

        dnf_drivers = dnf_drivers or {}
        damage_drivers = damage_drivers or []

        # Build entry lookup
        entry_by_driver: Dict[int, RaceEntry] = {
            e.driver.member_id: e for e in race.entries
        }

        results: List[RaceResult] = []
        total_distributed = 0.0

        # Calculate prize for finished drivers
        num_finishers = len(finishing_order)

        for position, driver_id in enumerate(finishing_order, start=1):
            entry = entry_by_driver.get(driver_id)
            if entry is None:
                continue

            entry.position = position
            entry.finished = True

            # Calculate prize
            if position in self.PRIZE_DISTRIBUTION:
                prize = race.prize_pool * self.PRIZE_DISTRIBUTION[position]
            elif position > 3 and num_finishers > 3:
                others_count = num_finishers - 3
                prize = (race.prize_pool * 0.05) / others_count
            else:
                prize = 0.0

            result = RaceResult(entry=entry, position=position, prize_won=prize)
            results.append(result)
            total_distributed += prize

            # Update driver stats
            self._update_driver_stats(entry.driver, position, prize, False)

        # Handle DNF drivers
        for driver_id, reason in dnf_drivers.items():
            entry = entry_by_driver.get(driver_id)
            if entry:
                entry.finished = False
                entry.dnf_reason = reason
                self._update_driver_stats(entry.driver, None, 0, True)

        # Handle car damage
        for driver_id in damage_drivers:
            entry = entry_by_driver.get(driver_id)
            if entry:
                self._inventory.set_car_condition(
                    entry.car.car_id, CarCondition.DAMAGED
                )

        # Add prize money to inventory
        self._inventory.add_funds(total_distributed)

        # Release all resources and update race status
        for entry in race.entries:
            entry.driver.is_available = True
            entry.car.is_available = True

        race.status = RaceStatus.COMPLETED

        outcome = RaceOutcome(
            race=race,
            results=results,
            total_prize_distributed=total_distributed
        )
        self._outcomes[race_id] = outcome

        return outcome

    def _update_driver_stats(self, driver: CrewMember, position: Optional[int],
                             prize: float, is_dnf: bool):
        """Update cumulative stats for a driver."""
        if driver.member_id not in self._driver_stats:
            self._driver_stats[driver.member_id] = DriverStats(
                driver_id=driver.member_id,
                driver_name=driver.name
            )

        stats = self._driver_stats[driver.member_id]
        stats.races_entered += 1
        stats.total_earnings += prize

        if is_dnf:
            stats.dnf_count += 1
        elif position is not None:
            if position == 1:
                stats.races_won += 1
            if position <= 3:
                stats.podium_finishes += 1

    def get_race_outcome(self, race_id: int) -> Optional[RaceOutcome]:
        """Get the outcome of a specific race."""
        return self._outcomes.get(race_id)

    def get_driver_stats(self, driver_id: int) -> Optional[DriverStats]:
        """Get cumulative stats for a driver."""
        return self._driver_stats.get(driver_id)

    def get_all_driver_stats(self) -> List[DriverStats]:
        """Get stats for all drivers."""
        return list(self._driver_stats.values())

    def get_rankings(self) -> List[DriverStats]:
        """Get driver rankings sorted by wins, then earnings."""
        stats = list(self._driver_stats.values())
        return sorted(
            stats,
            key=lambda s: (s.races_won, s.total_earnings),
            reverse=True
        )

    def get_top_earners(self, limit: int = 5) -> List[DriverStats]:
        """Get top earning drivers."""
        stats = list(self._driver_stats.values())
        return sorted(stats, key=lambda s: s.total_earnings, reverse=True)[:limit]

    def get_race_history(self) -> List[RaceOutcome]:
        """Get all recorded race outcomes."""
        return list(self._outcomes.values())

    def get_total_earnings(self) -> float:
        """Get total earnings across all races."""
        return sum(o.total_prize_distributed for o in self._outcomes.values())
