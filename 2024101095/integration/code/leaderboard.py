"""
Leaderboard Module (Custom Module 1)
=====================================
Tracks and displays crew performance rankings across races and missions.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .registration import CrewMember
from .results import ResultsModule, DriverStats


class LeaderboardType(Enum):
    """Types of leaderboards."""
    RACE_WINS = "race_wins"
    TOTAL_EARNINGS = "total_earnings"
    PODIUM_FINISHES = "podium_finishes"
    MISSIONS_COMPLETED = "missions_completed"
    OVERALL = "overall"  # Combined score


class TimePeriod(Enum):
    """Time periods for filtering."""
    ALL_TIME = "all_time"
    THIS_MONTH = "this_month"
    THIS_WEEK = "this_week"


@dataclass
class LeaderboardEntry:
    """A single entry in the leaderboard."""
    rank: int
    member: CrewMember
    score: float
    stat_detail: str  # Human-readable stat detail


@dataclass
class CrewPerformance:
    """Tracks overall performance for a crew member."""
    member_id: int
    race_wins: int = 0
    total_earnings: float = 0.0
    podium_finishes: int = 0
    races_entered: int = 0
    missions_completed: int = 0
    missions_failed: int = 0
    overall_score: float = 0.0

    def calculate_overall_score(self) -> float:
        """
        Calculate overall score based on weighted factors.

        Formula:
        - Race wins: 100 points each
        - Podium finishes: 50 points each
        - Missions completed: 25 points each
        - Earnings: 1 point per 1000 earned
        - Missions failed: -10 points each
        """
        self.overall_score = (
            (self.race_wins * 100) +
            (self.podium_finishes * 50) +
            (self.missions_completed * 25) +
            (self.total_earnings / 1000) -
            (self.missions_failed * 10)
        )
        return self.overall_score


@dataclass
class Achievement:
    """Represents an unlockable achievement."""
    achievement_id: str
    name: str
    description: str
    requirement: str
    points: int


# Built-in achievements
ACHIEVEMENTS = [
    Achievement("first_win", "First Victory",
                "Win your first race", "race_wins >= 1", 10),
    Achievement("podium_master", "Podium Master",
                "Finish in top 3 ten times", "podium_finishes >= 10", 50),
    Achievement("high_roller", "High Roller",
                "Earn 100,000 total", "total_earnings >= 100000", 100),
    Achievement("mission_specialist", "Mission Specialist",
                "Complete 10 missions", "missions_completed >= 10", 50),
    Achievement("perfect_record", "Perfect Record",
                "Complete 5 missions without failure",
                "missions_completed >= 5 and missions_failed == 0", 75),
    Achievement("race_veteran", "Race Veteran",
                "Enter 50 races", "races_entered >= 50", 25),
    Achievement("winner_winner", "Winner Winner",
                "Win 10 races", "race_wins >= 10", 100),
]


class LeaderboardModule:
    """
    Manages leaderboards and achievements.

    Depends on ResultsModule for race statistics.
    """

    def __init__(self, results: ResultsModule):
        self._results = results
        self._performance: Dict[int, CrewPerformance] = {}
        self._member_achievements: Dict[int, List[str]] = {}

    def _get_or_create_performance(self, member_id: int) -> CrewPerformance:
        """Get or create performance tracker for a member."""
        if member_id not in self._performance:
            self._performance[member_id] = CrewPerformance(member_id=member_id)
        return self._performance[member_id]

    def sync_from_results(self) -> None:
        """
        Synchronize performance data from results module.
        Note: get_all_driver_stats() returns a List[DriverStats].
        """
        all_stats = self._results.get_all_driver_stats()

        for stats in all_stats:
            perf = self._get_or_create_performance(stats.driver_id)
            perf.race_wins = stats.races_won
            perf.total_earnings = stats.total_earnings
            perf.podium_finishes = stats.podium_finishes
            perf.races_entered = stats.races_entered
            perf.calculate_overall_score()

    def record_mission_completion(self, member_id: int, success: bool,
                                  earnings: float = 0.0) -> None:
        """Record a mission completion for a member."""
        perf = self._get_or_create_performance(member_id)

        if success:
            perf.missions_completed += 1
            perf.total_earnings += earnings
        else:
            perf.missions_failed += 1

        perf.calculate_overall_score()
        self._check_achievements(member_id)

    def _check_achievements(self, member_id: int) -> List[Achievement]:
        """Check and award any newly earned achievements."""
        perf = self._performance.get(member_id)
        if not perf:
            return []

        if member_id not in self._member_achievements:
            self._member_achievements[member_id] = []

        earned = self._member_achievements[member_id]
        newly_earned = []

        for achievement in ACHIEVEMENTS:
            if achievement.achievement_id in earned:
                continue

            # Evaluate requirement safely
            requirement_met = eval(
                achievement.requirement,
                {"__builtins__": {}},
                {
                    "race_wins": perf.race_wins,
                    "total_earnings": perf.total_earnings,
                    "podium_finishes": perf.podium_finishes,
                    "missions_completed": perf.missions_completed,
                    "missions_failed": perf.missions_failed,
                    "races_entered": perf.races_entered,
                }
            )

            if requirement_met:
                earned.append(achievement.achievement_id)
                newly_earned.append(achievement)

        return newly_earned

    def get_achievements(self, member_id: int) -> List[Achievement]:
        """Get all achievements earned by a member."""
        earned_ids = self._member_achievements.get(member_id, [])
        return [a for a in ACHIEVEMENTS if a.achievement_id in earned_ids]

    def get_available_achievements(self, member_id: int) -> List[Achievement]:
        """Get achievements not yet earned by a member."""
        earned_ids = self._member_achievements.get(member_id, [])
        return [a for a in ACHIEVEMENTS if a.achievement_id not in earned_ids]

    def get_leaderboard(self, leaderboard_type: LeaderboardType,
                        limit: int = 10) -> List[LeaderboardEntry]:
        """
        Get a leaderboard sorted by the given type.

        Args:
            leaderboard_type: Type of leaderboard
            limit: Max entries to return

        Returns:
            List of LeaderboardEntry sorted by rank
        """
        self.sync_from_results()

        entries: List[Tuple[int, float, str]] = []

        for member_id, perf in self._performance.items():
            if leaderboard_type == LeaderboardType.RACE_WINS:
                score = float(perf.race_wins)
                detail = f"{perf.race_wins} wins"
            elif leaderboard_type == LeaderboardType.TOTAL_EARNINGS:
                score = perf.total_earnings
                detail = f"${perf.total_earnings:,.2f}"
            elif leaderboard_type == LeaderboardType.PODIUM_FINISHES:
                score = float(perf.podium_finishes)
                detail = f"{perf.podium_finishes} podiums"
            elif leaderboard_type == LeaderboardType.MISSIONS_COMPLETED:
                score = float(perf.missions_completed)
                detail = f"{perf.missions_completed} missions"
            else:  # OVERALL
                score = perf.overall_score
                detail = f"{perf.overall_score:.0f} points"

            entries.append((member_id, score, detail))

        # Sort by score descending
        entries.sort(key=lambda x: x[1], reverse=True)

        # Look up member objects from the results chain
        reg = self._results._race_mgmt._crew._registration

        leaderboard = []
        for rank, (member_id, score, detail) in enumerate(entries[:limit], 1):
            member = reg.get_member(member_id)
            if member:
                leaderboard.append(LeaderboardEntry(
                    rank=rank,
                    member=member,
                    score=score,
                    stat_detail=detail
                ))

        return leaderboard

    def get_member_performance(self, member_id: int) -> Optional[CrewPerformance]:
        """Get performance stats for a specific member."""
        self.sync_from_results()
        return self._performance.get(member_id)

    def get_member_rank(self, member_id: int,
                        leaderboard_type: LeaderboardType) -> Optional[int]:
        """Get a member's rank in a specific leaderboard."""
        leaderboard = self.get_leaderboard(leaderboard_type, limit=1000)
        for entry in leaderboard:
            if entry.member.member_id == member_id:
                return entry.rank
        return None

    def format_leaderboard(self, leaderboard_type: LeaderboardType,
                           limit: int = 10) -> str:
        """Format leaderboard as a string for display."""
        leaderboard = self.get_leaderboard(leaderboard_type, limit)

        if not leaderboard:
            return "No entries in leaderboard."

        lines = [f"=== {leaderboard_type.value.upper()} LEADERBOARD ===\n"]
        for entry in leaderboard:
            lines.append(
                f"{entry.rank}. {entry.member.name} - {entry.stat_detail}"
            )

        return "\n".join(lines)
