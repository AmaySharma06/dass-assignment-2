"""
Integration Tests – Race Management Module
===========================================
Tests how Race Management integrates with Crew Management and Inventory:
driver role validation, car availability, and race state transitions.
"""
import pytest
from integration.code import (
    Role, CarCondition,
    RaceStatus, InvalidEntryError, RaceNotFoundError,
    RaceManagementError, RaceManagementModule,
)
from integration.code.race_management import RaceType


class TestRaceManagementIntegration:
    """Race Management validates drivers + cars from Crew and Inventory."""

    def test_create_race_basic(self, race_management):
        """A race can be created and retrieved by ID."""
        race = race_management.create_race("Night Race", RaceType.CIRCUIT, 5_000.0)
        fetched = race_management.get_race(race.race_id)
        assert fetched is not None
        assert fetched.name == "Night Race"
        assert fetched.status == RaceStatus.SCHEDULED

    def test_enter_race_with_valid_driver_and_car(self, race_management):
        """A registered driver with the DRIVER role and a good car can enter."""
        driver = race_management._crew._registration.register_member("Racer", Role.DRIVER)
        car = race_management._inventory.add_car("Supra", "Toyota", 400)

        race = race_management.create_race("GP Night", RaceType.CIRCUIT, 3_000.0)
        entry = race_management.enter_race(race.race_id, driver.member_id, car.car_id)

        assert entry.driver.member_id == driver.member_id
        assert entry.car.car_id == car.car_id

    def test_entering_race_marks_driver_unavailable(self, race_management):
        """After entering a race, the driver is marked unavailable."""
        driver = race_management._crew._registration.register_member("D", Role.DRIVER)
        car = race_management._inventory.add_car("Car", "Model", 300)
        race = race_management.create_race("R", RaceType.DRAG, 1_000.0)

        assert driver.is_available is True
        race_management.enter_race(race.race_id, driver.member_id, car.car_id)
        assert driver.is_available is False

    def test_entering_race_marks_car_unavailable(self, race_management):
        """After entering a race, the car is marked unavailable."""
        driver = race_management._crew._registration.register_member("D2", Role.DRIVER)
        car = race_management._inventory.add_car("Viper", "Dodge", 600)
        race = race_management.create_race("R2", RaceType.SPRINT, 2_000.0)

        race_management.enter_race(race.race_id, driver.member_id, car.car_id)
        assert car.is_available is False

    def test_non_driver_cannot_enter_race(self, race_management):
        """Only DRIVER role members can enter a race."""
        mechanic = race_management._crew._registration.register_member("Wrench", Role.MECHANIC)
        car = race_management._inventory.add_car("Car", "Sedan", 200)
        race = race_management.create_race("GP", RaceType.DRAG, 1_000.0)

        with pytest.raises(InvalidEntryError):
            race_management.enter_race(race.race_id, mechanic.member_id, car.car_id)

    def test_unavailable_driver_cannot_enter(self, race_management):
        """A driver already in use cannot be entered again."""
        driver = race_management._crew._registration.register_member("Busy", Role.DRIVER)
        c1 = race_management._inventory.add_car("C1", "Model", 300)
        c2 = race_management._inventory.add_car("C2", "Model", 300)

        race1 = race_management.create_race("R1", RaceType.SPRINT, 1_000.0)
        race2 = race_management.create_race("R2", RaceType.SPRINT, 1_000.0)

        race_management.enter_race(race1.race_id, driver.member_id, c1.car_id)

        with pytest.raises(InvalidEntryError):
            race_management.enter_race(race2.race_id, driver.member_id, c2.car_id)

    def test_same_car_cannot_be_double_entered(self, race_management):
        """A car already in a race cannot be used in another entry."""
        d1 = race_management._crew._registration.register_member("D1", Role.DRIVER)
        d2 = race_management._crew._registration.register_member("D2", Role.DRIVER)
        car = race_management._inventory.add_car("Only Car", "Sports", 400)

        race = race_management.create_race("GP", RaceType.CIRCUIT, 3_000.0)
        race_management.enter_race(race.race_id, d1.member_id, car.car_id)

        with pytest.raises(InvalidEntryError):
            race_management.enter_race(race.race_id, d2.member_id, car.car_id)

    def test_damaged_car_cannot_enter_race(self, race_management):
        """A damaged car is rejected when entering a race."""
        driver = race_management._crew._registration.register_member("D", Role.DRIVER)
        car = race_management._inventory.add_car("Clunker", "Unknown", 150)
        race_management._inventory.set_car_condition(car.car_id, CarCondition.DAMAGED)

        race = race_management.create_race("Race", RaceType.DRAG, 500.0)

        with pytest.raises(InvalidEntryError):
            race_management.enter_race(race.race_id, driver.member_id, car.car_id)

    def test_start_race_requires_entries(self, race_management):
        """A race with no entries cannot be started."""
        race = race_management.create_race("Empty Race", RaceType.CIRCUIT, 1_000.0)
        with pytest.raises(RaceManagementError):
            race_management.start_race(race.race_id)

    def test_start_race_changes_status(self, race_management):
        """Starting a race changes its status to IN_PROGRESS."""
        driver = race_management._crew._registration.register_member("D", Role.DRIVER)
        car = race_management._inventory.add_car("Car", "Model", 300)
        race = race_management.create_race("Night GP", RaceType.CIRCUIT, 2_000.0)
        race_management.enter_race(race.race_id, driver.member_id, car.car_id)

        race_management.start_race(race.race_id)
        assert race.status == RaceStatus.IN_PROGRESS

    def test_cancel_race_releases_resources(self, race_management):
        """Cancelling a race makes driver and car available again."""
        driver = race_management._crew._registration.register_member("D", Role.DRIVER)
        car = race_management._inventory.add_car("Car", "Model", 300)
        race = race_management.create_race("To Cancel", RaceType.SPRINT, 1_000.0)
        race_management.enter_race(race.race_id, driver.member_id, car.car_id)

        assert driver.is_available is False
        race_management.cancel_race(race.race_id)
        assert driver.is_available is True
        assert car.is_available is True

    def test_get_suitable_cars_sorted_by_horsepower_for_drag(self, race_management):
        """For DRAG races, suitable cars are sorted by horsepower descending."""
        race_management._inventory.add_car("Slow", "Sedan", 150)
        race_management._inventory.add_car("Fast", "Sports", 600)
        race_management._inventory.add_car("Medium", "Coupe", 300)

        cars = race_management.get_suitable_cars_for_race(RaceType.DRAG)
        assert cars[0].horsepower >= cars[1].horsepower
