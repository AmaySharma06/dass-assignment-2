"""
Integration Tests – Full System End-to-End
============================================
Tests complex workflows that span all modules together:
Registration → Crew → Inventory → Race → Results → Notifications → Leaderboard
"""
import pytest
from integration.code import (
    Role, MissionType, MissionStatus, RaceStatus,
    InvalidEntryError, LeaderboardType, NotificationCategory,
)
from integration.code.race_management import RaceType


class TestFullSystemWorkflow:
    """End-to-end scenarios exercising all eight modules together."""

    def test_complete_race_workflow(self, full_system):
        """
        Full lifecycle: register drivers → add cars → create race →
        enter entries → start → record results → verify stats and prize money.
        """
        reg = full_system['registration']
        inv = full_system['inventory']
        race_mgmt = full_system['race']
        results = full_system['results']
        notif = full_system['notifications']

        # Register crew
        d1 = reg.register_member("Lightning", Role.DRIVER)
        d2 = reg.register_member("Thunder", Role.DRIVER)

        # Add cars
        c1 = inv.add_car("Speed Demon", "Sports", 450)
        c2 = inv.add_car("Road Runner", "Sports", 440)

        # Create and fill race
        race = race_mgmt.create_race("Championship Final", RaceType.CIRCUIT, 10_000.0)
        race_mgmt.enter_race(race.race_id, d1.member_id, c1.car_id)
        race_mgmt.enter_race(race.race_id, d2.member_id, c2.car_id)

        # Notify and start
        notif.notify_race_starting(race.race_id, race.name)
        race_mgmt.start_race(race.race_id)

        # Record results — d1 wins
        initial_balance = inv.get_balance()
        outcome = results.record_race_results(
            race.race_id,
            finishing_order=[d1.member_id, d2.member_id]
        )

        # Validate outcome
        assert outcome.results[0].position == 1
        assert outcome.results[0].entry.driver.member_id == d1.member_id

        # Prize added to inventory
        assert inv.get_balance() > initial_balance

        # Stats updated
        stats1 = results.get_driver_stats(d1.member_id)
        assert stats1.races_won == 1

        stats2 = results.get_driver_stats(d2.member_id)
        assert stats2.races_won == 0

        # Resources released
        assert d1.is_available is True
        assert c1.is_available is True

    def test_complete_mission_workflow(self, full_system):
        """
        Full lifecycle: register crew → create mission → assign crew + car →
        start mission → complete → verify balance and status.
        """
        crew = full_system['crew']
        inv = full_system['inventory']
        mission_mod = full_system['mission']
        notif = full_system['notifications']

        driver = crew._registration.register_member("Rescue Driver", Role.DRIVER)
        mechanic = crew._registration.register_member("Rescue Mech", Role.MECHANIC)
        car = inv.add_car("Rescue Vehicle", "SUV", 300)

        initial_balance = inv.get_balance()

        m = mission_mod.create_mission("Emergency Rescue", MissionType.RESCUE, 5_000.0)
        notif.notify_mission_available("Emergency Rescue", 5_000.0)

        # Check role availability
        assert mission_mod.can_start_mission(MissionType.RESCUE) is True

        # Assign crew and car
        mission_mod.assign_crew_to_mission(m.mission_id, driver.member_id, Role.DRIVER)
        mission_mod.assign_crew_to_mission(m.mission_id, mechanic.member_id, Role.MECHANIC)
        mission_mod.assign_car_to_mission(m.mission_id, car.car_id)

        assert driver.is_available is False
        assert mechanic.is_available is False

        # Run mission
        mission_mod.start_mission(m.mission_id)
        assert m.status == MissionStatus.IN_PROGRESS

        mission_mod.complete_mission(m.mission_id, success=True)

        # Verify completion
        assert m.status == MissionStatus.COMPLETED
        assert driver.is_available is True
        assert mechanic.is_available is True
        assert car.is_available is True
        assert inv.get_balance() == initial_balance + 5_000.0

    def test_resource_conflict_driver_double_booked(self, full_system):
        """
        A driver assigned to a mission cannot simultaneously enter a race.
        """
        crew = full_system['crew']
        inv = full_system['inventory']
        mission_mod = full_system['mission']
        race_mgmt = full_system['race']

        driver = crew._registration.register_member("Busy Driver", Role.DRIVER)
        car = inv.add_car("Only Car", "Sports", 400)

        # Lock driver in a mission
        m = mission_mod.create_mission("Job", MissionType.DELIVERY, 1_000.0)
        mission_mod.assign_crew_to_mission(m.mission_id, driver.member_id, Role.DRIVER)
        mission_mod.assign_car_to_mission(m.mission_id, car.car_id)

        # Try to enter the same driver+car in a race
        race = race_mgmt.create_race("Race", RaceType.SPRINT, 1_000.0)
        with pytest.raises(InvalidEntryError):
            race_mgmt.enter_race(race.race_id, driver.member_id, car.car_id)

    def test_leaderboard_reflects_race_winners(self, full_system):
        """
        After a race, the leaderboard should rank the winner at position 1.
        """
        reg = full_system['registration']
        inv = full_system['inventory']
        race_mgmt = full_system['race']
        results = full_system['results']
        leaderboard = full_system['leaderboard']

        d1 = reg.register_member("Champ", Role.DRIVER)
        d2 = reg.register_member("Runner", Role.DRIVER)
        c1 = inv.add_car("Rocket", "Sports", 500)
        c2 = inv.add_car("Jet", "Sports", 490)

        race = race_mgmt.create_race("Final", RaceType.CIRCUIT, 8_000.0)
        race_mgmt.enter_race(race.race_id, d1.member_id, c1.car_id)
        race_mgmt.enter_race(race.race_id, d2.member_id, c2.car_id)
        race_mgmt.start_race(race.race_id)
        results.record_race_results(race.race_id,
                                    finishing_order=[d1.member_id, d2.member_id])

        leaderboard.sync_from_results()
        board = leaderboard.get_leaderboard(LeaderboardType.RACE_WINS)
        assert board[0].member.member_id == d1.member_id

    def test_notifications_sent_during_race_and_mission(self, full_system):
        """
        Race and mission events generate the expected notifications.
        """
        reg = full_system['registration']
        inv = full_system['inventory']
        race_mgmt = full_system['race']
        results = full_system['results']
        notif = full_system['notifications']

        driver = reg.register_member("Notif Driver", Role.DRIVER)
        car = inv.add_car("Fast Car", "Model", 400)

        race = race_mgmt.create_race("Notif Race", RaceType.CIRCUIT, 5_000.0)
        race_mgmt.enter_race(race.race_id, driver.member_id, car.car_id)

        notif.notify_race_starting(race.race_id, race.name, member_id=driver.member_id)
        race_mgmt.start_race(race.race_id)
        results.record_race_results(race.race_id, finishing_order=[driver.member_id])

        notif.notify_race_result(race.race_id, 1, driver.member_id, 2_500.0)

        member_notifs = notif.get_notifications_for_member(driver.member_id)
        categories = {n.category for n in member_notifs}
        assert NotificationCategory.RACE in categories

    def test_mission_failure_does_not_add_funds(self, full_system):
        """
        A failed mission should not increase the inventory balance.
        """
        crew = full_system['crew']
        inv = full_system['inventory']
        mission_mod = full_system['mission']

        driver = crew._registration.register_member("Risky Driver", Role.DRIVER)
        car = inv.add_car("Clunker", "Unknown", 100)
        before = inv.get_balance()

        m = mission_mod.create_mission("Gamble", MissionType.DELIVERY, 999.0)
        mission_mod.assign_crew_to_mission(m.mission_id, driver.member_id, Role.DRIVER)
        mission_mod.assign_car_to_mission(m.mission_id, car.car_id)
        mission_mod.start_mission(m.mission_id)
        mission_mod.complete_mission(m.mission_id, success=False)

        assert inv.get_balance() == before
        assert m.status == MissionStatus.FAILED

    def test_multiple_races_accumulate_driver_stats(self, full_system):
        """
        Stats accumulate correctly across multiple race wins.
        """
        reg = full_system['registration']
        inv = full_system['inventory']
        race_mgmt = full_system['race']
        results = full_system['results']

        driver = reg.register_member("Veteran", Role.DRIVER)

        for i in range(3):
            car = inv.add_car(f"Car{i}", "Sports", 400)
            race = race_mgmt.create_race(f"Race {i}", RaceType.CIRCUIT, 2_000.0)
            race_mgmt.enter_race(race.race_id, driver.member_id, car.car_id)
            race_mgmt.start_race(race.race_id)
            results.record_race_results(race.race_id, finishing_order=[driver.member_id])

        stats = results.get_driver_stats(driver.member_id)
        assert stats.races_entered == 3
        assert stats.races_won == 3
        assert stats.podium_finishes == 3
