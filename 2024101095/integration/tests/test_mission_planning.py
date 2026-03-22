"""
Integration Tests – Mission Planning Module
==============================================
Tests how Mission Planning integrates with Crew Management and Inventory:
role validation, resource locking, reward distribution, and car damage.
"""
import pytest
from integration.code import (
    Role, CarCondition,
    MissionType, MissionStatus,
    MissionError, RoleUnavailableError, MissionPlanningModule,
)


class TestMissionPlanningIntegration:
    """Mission Planning validates crew availability through Crew Management."""

    def test_delivery_requires_driver(self, mission_planning):
        """DELIVERY missions need exactly one DRIVER."""
        crew = mission_planning._crew
        assert mission_planning.can_start_mission(MissionType.DELIVERY) is False

        crew._registration.register_member("Driver", Role.DRIVER)
        assert mission_planning.can_start_mission(MissionType.DELIVERY) is True

    def test_rescue_requires_driver_and_mechanic(self, mission_planning):
        """RESCUE missions need both DRIVER and MECHANIC."""
        crew = mission_planning._crew

        missing = set(mission_planning.get_missing_roles(MissionType.RESCUE))
        assert Role.DRIVER in missing
        assert Role.MECHANIC in missing

        crew._registration.register_member("Driver", Role.DRIVER)
        missing = set(mission_planning.get_missing_roles(MissionType.RESCUE))
        assert Role.DRIVER not in missing
        assert Role.MECHANIC in missing

        crew._registration.register_member("Mech", Role.MECHANIC)
        assert mission_planning.can_start_mission(MissionType.RESCUE) is True

    def test_assigning_crew_marks_unavailable(self, mission_planning):
        """A crew member assigned to a mission becomes unavailable."""
        driver = mission_planning._crew._registration.register_member("D", Role.DRIVER)
        assert driver.is_available is True

        mission = mission_planning.create_mission("Job", MissionType.DELIVERY, 1_000.0)
        mission_planning.assign_crew_to_mission(mission.mission_id, driver.member_id, Role.DRIVER)
        assert driver.is_available is False

    def test_mission_needs_car_for_driver_role(self, mission_planning):
        """A mission with a DRIVER role cannot start without an assigned car."""
        driver = mission_planning._crew._registration.register_member("D", Role.DRIVER)
        mission = mission_planning.create_mission("Careless", MissionType.DELIVERY, 100.0)
        mission_planning.assign_crew_to_mission(mission.mission_id, driver.member_id, Role.DRIVER)

        with pytest.raises(MissionError, match="car"):
            mission_planning.start_mission(mission.mission_id)

    def test_complete_mission_releases_crew_and_car(self, mission_planning):
        """Completing a mission frees crew member and car."""
        crew = mission_planning._crew
        inv = mission_planning._inventory

        driver = crew._registration.register_member("Driver", Role.DRIVER)
        car = inv.add_car("Van", "Ford", 200)

        mission = mission_planning.create_mission("Delivery", MissionType.DELIVERY, 2_000.0)
        mission_planning.assign_crew_to_mission(mission.mission_id, driver.member_id, Role.DRIVER)
        mission_planning.assign_car_to_mission(mission.mission_id, car.car_id)
        mission_planning.start_mission(mission.mission_id)

        assert driver.is_available is False
        assert car.is_available is False

        mission_planning.complete_mission(mission.mission_id, success=True)
        assert driver.is_available is True
        assert car.is_available is True

    def test_successful_mission_credits_reward(self, mission_planning):
        """Completing a mission successfully adds reward to inventory."""
        inv = mission_planning._inventory
        before = inv.get_balance()

        driver = mission_planning._crew._registration.register_member("D", Role.DRIVER)
        car = inv.add_car("Truck", "Chevy", 250)

        mission = mission_planning.create_mission("Payday", MissionType.DELIVERY, 3_000.0)
        mission_planning.assign_crew_to_mission(mission.mission_id, driver.member_id, Role.DRIVER)
        mission_planning.assign_car_to_mission(mission.mission_id, car.car_id)
        mission_planning.start_mission(mission.mission_id)
        mission_planning.complete_mission(mission.mission_id, success=True)

        assert inv.get_balance() == before + 3_000.0

    def test_failed_mission_no_reward(self, mission_planning):
        """A failed mission does not credit any reward."""
        inv = mission_planning._inventory
        before = inv.get_balance()

        driver = mission_planning._crew._registration.register_member("D", Role.DRIVER)
        car = inv.add_car("Clunker", "Unknown", 100)

        mission = mission_planning.create_mission("Gamble", MissionType.DELIVERY, 500.0)
        mission_planning.assign_crew_to_mission(mission.mission_id, driver.member_id, Role.DRIVER)
        mission_planning.assign_car_to_mission(mission.mission_id, car.car_id)
        mission_planning.start_mission(mission.mission_id)
        mission_planning.complete_mission(mission.mission_id, success=False)

        assert inv.get_balance() == before

    def test_car_damaged_during_mission_updates_condition(self, mission_planning):
        """A car that is damaged during a mission gets DAMAGED condition."""
        inv = mission_planning._inventory
        driver = mission_planning._crew._registration.register_member("D", Role.DRIVER)
        car = inv.add_car("Risky Car", "Coupe", 300)

        mission = mission_planning.create_mission("Risky Run", MissionType.DELIVERY, 1_000.0)
        mission_planning.assign_crew_to_mission(mission.mission_id, driver.member_id, Role.DRIVER)
        mission_planning.assign_car_to_mission(mission.mission_id, car.car_id)
        mission_planning.start_mission(mission.mission_id)
        mission_planning.complete_mission(mission.mission_id, success=True, car_damaged=True)

        assert car.condition == CarCondition.DAMAGED

    def test_cancel_mission_releases_resources(self, mission_planning):
        """Cancelling a mission in ASSIGNED state frees crew and car."""
        crew = mission_planning._crew
        inv = mission_planning._inventory

        driver = crew._registration.register_member("D", Role.DRIVER)
        car = inv.add_car("Car", "Model", 200)

        mission = mission_planning.create_mission("Cancel This", MissionType.DELIVERY)
        mission_planning.assign_crew_to_mission(mission.mission_id, driver.member_id, Role.DRIVER)
        mission_planning.assign_car_to_mission(mission.mission_id, car.car_id)

        mission_planning.cancel_mission(mission.mission_id)

        assert driver.is_available is True
        assert car.is_available is True
        assert mission.status == MissionStatus.CANCELLED

    def test_auto_assign_selects_best_available(self, mission_planning):
        """auto_assign_mission picks highest-skill driver."""
        crew = mission_planning._crew
        inv = mission_planning._inventory

        low = crew._registration.register_member("Low", Role.DRIVER)
        high = crew._registration.register_member("High", Role.DRIVER)

        crew.update_skill_level(low.member_id, 3)
        crew.update_skill_level(high.member_id, 9)

        inv.add_car("Getaway Van", "Dodge", 350)

        mission = mission_planning.create_mission("Auto Job", MissionType.DELIVERY, 1_000.0)
        mission_planning.auto_assign_mission(mission.mission_id)

        # High-skill driver should be assigned (is now unavailable)
        assert high.is_available is False
        assert low.is_available is True
