"""
Integration Tests – Results Module
=====================================
Tests how Results integrates with Race Management and Inventory:
prize distribution, driver stats, car damage, and resource release.
"""
import pytest
from integration.code import (
    Role, CarCondition, RaceStatus, ResultsError, ResultsModule
)
from integration.code.race_management import RaceType


class TestResultsIntegration:
    """Results module records outcomes across Race Management and Inventory."""

    def _setup_and_start_race(self, results, num_drivers=2, prize_pool=10_000.0):
        """Helper: register drivers, cars, create race, and start it."""
        rm = results._race_mgmt
        drivers = []
        for i in range(num_drivers):
            d = rm._crew._registration.register_member(f"Driver{i}", Role.DRIVER)
            c = rm._inventory.add_car(f"Car{i}", "Sports", 400 + i * 10)
            drivers.append((d, c))

        race = rm.create_race("Finals", RaceType.CIRCUIT, prize_pool=prize_pool)
        for d, c in drivers:
            rm.enter_race(race.race_id, d.member_id, c.car_id)
        rm.start_race(race.race_id)
        return race, drivers

    def test_winner_gets_50_percent_prize(self, results):
        """First place driver receives 50% of the prize pool."""
        race, drivers = self._setup_and_start_race(results, prize_pool=10_000.0)
        d1, _c1 = drivers[0]
        d2, _c2 = drivers[1]

        outcome = results.record_race_results(
            race.race_id, finishing_order=[d1.member_id, d2.member_id]
        )
        winner_result = next(r for r in outcome.results if r.position == 1)
        assert winner_result.prize_won == 5_000.0

    def test_prize_added_to_inventory(self, results):
        """Prize money is added to the inventory cash balance."""
        inv = results._inventory
        before = inv.get_balance()

        race, drivers = self._setup_and_start_race(results, prize_pool=10_000.0)
        d1, _ = drivers[0]
        d2, _ = drivers[1]

        outcome = results.record_race_results(
            race.race_id, finishing_order=[d1.member_id, d2.member_id]
        )
        assert inv.get_balance() > before

    def test_driver_stats_record_win(self, results):
        """Winning a race increments races_won in driver stats."""
        race, drivers = self._setup_and_start_race(results)
        winner, _ = drivers[0]
        loser, _ = drivers[1]

        results.record_race_results(
            race.race_id, finishing_order=[winner.member_id, loser.member_id]
        )

        stats = results.get_driver_stats(winner.member_id)
        assert stats is not None
        assert stats.races_won == 1
        assert stats.races_entered == 1

    def test_runner_up_not_counted_as_winner(self, results):
        """Second place driver has races_won == 0."""
        race, drivers = self._setup_and_start_race(results)
        winner, _ = drivers[0]
        runner_up, _ = drivers[1]

        results.record_race_results(
            race.race_id, finishing_order=[winner.member_id, runner_up.member_id]
        )

        stats = results.get_driver_stats(runner_up.member_id)
        assert stats.races_won == 0
        assert stats.races_entered == 1

    def test_podium_finishes_tracked(self, results):
        """Finishes in positions 1-3 are counted as podium finishes."""
        rm = results._race_mgmt
        drivers = []
        for i in range(3):
            d = rm._crew._registration.register_member(f"P{i}", Role.DRIVER)
            c = rm._inventory.add_car(f"Car{i}", "Sports", 350 + i)
            drivers.append((d, c))

        race = rm.create_race("Podium Race", RaceType.CIRCUIT, 9_000.0)
        for d, c in drivers:
            rm.enter_race(race.race_id, d.member_id, c.car_id)
        rm.start_race(race.race_id)

        finishing_order = [d.member_id for d, _ in drivers]
        results.record_race_results(race.race_id, finishing_order=finishing_order)

        for d, _ in drivers:
            stats = results.get_driver_stats(d.member_id)
            assert stats.podium_finishes == 1

    def test_resources_released_after_race(self, results):
        """After recording results, drivers and cars become available again."""
        race, drivers = self._setup_and_start_race(results)
        d1, c1 = drivers[0]
        d2, c2 = drivers[1]

        # Should be unavailable during race
        assert d1.is_available is False
        assert c1.is_available is False

        results.record_race_results(
            race.race_id, finishing_order=[d1.member_id, d2.member_id]
        )
        assert d1.is_available is True
        assert c1.is_available is True

    def test_car_damage_recorded_in_inventory(self, results):
        """Cars marked as damaged by damage_drivers get DAMAGED condition."""
        race, drivers = self._setup_and_start_race(results)
        d1, c1 = drivers[0]
        d2, c2 = drivers[1]

        results.record_race_results(
            race.race_id,
            finishing_order=[d1.member_id, d2.member_id],
            damage_drivers=[d1.member_id]
        )
        assert c1.condition == CarCondition.DAMAGED
        assert c2.condition == CarCondition.GOOD

    def test_dnf_driver_gets_no_prize(self, results):
        """DNF drivers do not receive any prize money."""
        race, drivers = self._setup_and_start_race(results, num_drivers=2,
                                                   prize_pool=5_000.0)
        finisher, _ = drivers[0]
        dnf_driver, _ = drivers[1]

        results.record_race_results(
            race.race_id,
            finishing_order=[finisher.member_id],
            dnf_drivers={dnf_driver.member_id: "Engine failure"}
        )

        dnf_stats = results.get_driver_stats(dnf_driver.member_id)
        assert dnf_stats.dnf_count == 1
        assert dnf_stats.total_earnings == 0.0

    def test_rankings_sorted_by_wins_then_earnings(self, results):
        """get_rankings returns drivers ordered by wins desc, earnings desc."""
        race, drivers = self._setup_and_start_race(results)
        d1, _ = drivers[0]
        d2, _ = drivers[1]

        results.record_race_results(
            race.race_id, finishing_order=[d1.member_id, d2.member_id]
        )

        rankings = results.get_rankings()
        assert rankings[0].driver_id == d1.member_id

    def test_cannot_record_results_for_non_in_progress_race(self, results):
        """Recording results for a SCHEDULED race raises ResultsError."""
        rm = results._race_mgmt
        race = rm.create_race("Not Started", RaceType.DRAG, 1_000.0)

        with pytest.raises(ResultsError):
            results.record_race_results(race.race_id, finishing_order=[])
