"""
Integration Tests – Leaderboard Module (Custom Module 1)
==========================================================
Tests how Leaderboard integrates with Results:
sync of stats, ranking by type, and achievement unlocking.
"""
import pytest
from integration.code import (
    Role, LeaderboardType, LeaderboardModule,
)
from integration.code.race_management import RaceType


def _run_race_and_record(results, winner_name="Winner", loser_name="Loser",
                         prize_pool=10_000.0):
    """Helper: set up a full race and record results."""
    rm = results._race_mgmt
    winner = rm._crew._registration.register_member(winner_name, Role.DRIVER)
    loser = rm._crew._registration.register_member(loser_name, Role.DRIVER)
    c1 = rm._inventory.add_car("Car1", "Model", 400)
    c2 = rm._inventory.add_car("Car2", "Model", 400)

    race = rm.create_race("Race", RaceType.CIRCUIT, prize_pool=prize_pool)
    rm.enter_race(race.race_id, winner.member_id, c1.car_id)
    rm.enter_race(race.race_id, loser.member_id, c2.car_id)
    rm.start_race(race.race_id)
    results.record_race_results(race.race_id,
                                finishing_order=[winner.member_id, loser.member_id])
    return winner, loser


class TestLeaderboardIntegration:
    """Leaderboard syncs data from Results and calculates rankings."""

    def test_leaderboard_starts_empty(self, leaderboard):
        """Fresh leaderboard has no entries."""
        board = leaderboard.get_leaderboard(LeaderboardType.RACE_WINS)
        assert board == []

    def test_leaderboard_populated_after_race(self, leaderboard, results):
        """After a race is recorded, leaderboard reflects the results."""
        winner, _ = _run_race_and_record(results)
        leaderboard.sync_from_results()

        board = leaderboard.get_leaderboard(LeaderboardType.RACE_WINS, limit=5)
        assert len(board) >= 1
        assert board[0].member.member_id == winner.member_id

    def test_earnings_leaderboard_reflects_prizes(self, leaderboard, results):
        """Total earnings leaderboard shows the correct amounts."""
        winner, _ = _run_race_and_record(results, prize_pool=10_000.0)
        leaderboard.sync_from_results()

        board = leaderboard.get_leaderboard(LeaderboardType.TOTAL_EARNINGS)
        assert board[0].member.member_id == winner.member_id
        # Winner gets 50% of 10000 = 5000
        assert board[0].score == 5_000.0

    def test_overall_leaderboard_uses_combined_score(self, leaderboard, results):
        """OVERALL leaderboard uses the weighted formula."""
        winner, loser = _run_race_and_record(results)
        leaderboard.sync_from_results()

        board = leaderboard.get_leaderboard(LeaderboardType.OVERALL)
        # winner should be ranked higher
        winner_entry = next((e for e in board if e.member.member_id == winner.member_id), None)
        assert winner_entry is not None
        assert winner_entry.rank == 1

    def test_mission_completions_recorded_separately(self, leaderboard):
        """Mission completions can be tracked independently of race results."""
        leaderboard.record_mission_completion(member_id=42, success=True, earnings=500.0)

        perf = leaderboard._performance.get(42)
        assert perf is not None
        assert perf.missions_completed == 1
        assert perf.total_earnings == 500.0

    def test_mission_failures_reduce_score(self, leaderboard):
        """Failed missions reduce the overall score."""
        leaderboard.record_mission_completion(member_id=7, success=True)
        score_after_win = leaderboard._performance[7].overall_score

        leaderboard.record_mission_completion(member_id=7, success=False)
        score_after_fail = leaderboard._performance[7].overall_score

        assert score_after_fail < score_after_win

    def test_first_win_achievement_unlocked(self, leaderboard, results):
        """A driver who wins their first race earns 'first_win' achievement."""
        winner, _ = _run_race_and_record(results)
        leaderboard.sync_from_results()
        # Trigger achievement check by re-syncing (sync doesn't check achievements)
        # Manually trigger for now via record_mission_completion path
        # or check after explicit sync_from_results + check
        leaderboard._check_achievements(winner.member_id)
        achievements = leaderboard.get_achievements(winner.member_id)
        achieved_ids = [a.achievement_id for a in achievements]
        assert "first_win" in achieved_ids

    def test_get_member_rank(self, leaderboard, results):
        """get_member_rank returns correct rank for a driver."""
        winner, loser = _run_race_and_record(results)
        leaderboard.sync_from_results()
        leaderboard._check_achievements(winner.member_id)

        rank = leaderboard.get_member_rank(winner.member_id, LeaderboardType.RACE_WINS)
        assert rank == 1

    def test_format_leaderboard_returns_string(self, leaderboard, results):
        """format_leaderboard returns a non-empty readable string."""
        _run_race_and_record(results)
        leaderboard.sync_from_results()

        output = leaderboard.format_leaderboard(LeaderboardType.RACE_WINS)
        assert isinstance(output, str)
        assert "LEADERBOARD" in output
