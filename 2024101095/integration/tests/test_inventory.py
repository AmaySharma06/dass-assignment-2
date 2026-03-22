"""
Integration Tests – Inventory Module
======================================
Tests that cars, funds, parts, and tools are tracked correctly.
"""
import pytest
from integration.code import (
    CarCondition, InsufficientFundsError, ItemNotFoundError, InventoryModule
)


class TestInventoryModule:
    """Test inventory tracking — cars, cash, parts, tools."""

    def test_initial_balance(self, inventory):
        """Starting balance is set at creation time."""
        assert inventory.get_balance() == 10_000.0

    def test_add_funds(self, inventory):
        """Adding funds increases the balance."""
        inventory.add_funds(5_000.0)
        assert inventory.get_balance() == 15_000.0

    def test_deduct_funds(self, inventory):
        """Deducting funds decreases the balance."""
        inventory.deduct_funds(3_000.0)
        assert inventory.get_balance() == 7_000.0

    def test_deduct_more_than_balance_raises(self, inventory):
        """Deducting more than available raises InsufficientFundsError."""
        with pytest.raises(InsufficientFundsError):
            inventory.deduct_funds(999_999.0)

    def test_add_negative_amount_raises(self, inventory):
        """Adding a non-positive amount raises ValueError."""
        with pytest.raises(ValueError):
            inventory.add_funds(-100.0)

    def test_add_car_and_retrieve(self, inventory):
        """A car added to inventory can be retrieved by ID."""
        car = inventory.add_car("Eclipse", "Mitsubishi", 280)
        retrieved = inventory.get_car(car.car_id)
        assert retrieved is not None
        assert retrieved.name == "Eclipse"
        assert retrieved.model == "Mitsubishi"
        assert retrieved.horsepower == 280

    def test_default_car_condition_is_good(self, inventory):
        """Cars are added in GOOD condition by default."""
        car = inventory.add_car("Civic", "Honda", 200)
        assert car.condition == CarCondition.GOOD

    def test_set_car_condition(self, inventory):
        """Car condition can be updated."""
        car = inventory.add_car("Supra", "Toyota", 380)
        inventory.set_car_condition(car.car_id, CarCondition.DAMAGED)
        assert car.condition == CarCondition.DAMAGED

    def test_get_available_cars_excludes_unavailable(self, inventory):
        """get_available_cars excludes unavailable or totaled cars."""
        c1 = inventory.add_car("Charger", "Dodge", 450)
        c2 = inventory.add_car("Challenger", "Dodge", 420)

        c1.is_available = False
        available = inventory.get_available_cars()
        ids = [c.car_id for c in available]
        assert c1.car_id not in ids
        assert c2.car_id in ids

    def test_get_race_ready_cars(self, inventory):
        """get_race_ready_cars excludes damaged cars."""
        good_car = inventory.add_car("GTR", "Nissan", 550)
        bad_car = inventory.add_car("Beater", "Generic", 100)
        inventory.set_car_condition(bad_car.car_id, CarCondition.DAMAGED)

        race_ready = inventory.get_race_ready_cars()
        ids = [c.car_id for c in race_ready]
        assert good_car.car_id in ids
        assert bad_car.car_id not in ids

    def test_repair_car_restores_condition(self, inventory):
        """repair_car restores a damaged car to GOOD condition."""
        car = inventory.add_car("Old Banger", "Unknown", 120)
        inventory.set_car_condition(car.car_id, CarCondition.DAMAGED)
        inventory.repair_car(car.car_id, 500.0)
        assert car.condition == CarCondition.GOOD

    def test_repair_costs_money(self, inventory):
        """repair_car deducts the repair cost from the balance."""
        car = inventory.add_car("Car", "Model", 200)
        inventory.set_car_condition(car.car_id, CarCondition.DAMAGED)
        before = inventory.get_balance()
        inventory.repair_car(car.car_id, 1_000.0)
        assert inventory.get_balance() == before - 1_000.0

    def test_add_part_and_use(self, inventory):
        """Parts can be added and quantities decremented."""
        part = inventory.add_part("Engine Filter", 10, 25.0)
        inventory.use_parts(part.part_id, 3)
        updated = inventory.get_part(part.part_id)
        assert updated.quantity == 7

    def test_use_more_parts_than_available_raises(self, inventory):
        """Using more parts than in stock raises ValueError."""
        part = inventory.add_part("Brake Pad", 2, 40.0)
        with pytest.raises(ValueError):
            inventory.use_parts(part.part_id, 5)

    def test_add_tool_and_list(self, inventory):
        """Tools can be added and listed."""
        inventory.add_tool("Impact Wrench")
        inventory.add_tool("Jack Stand")
        tools = inventory.get_available_tools()
        assert len(tools) == 2

    def test_inventory_summary(self, inventory):
        """get_inventory_summary returns a dict with expected keys."""
        inventory.add_car("Car", "Model", 200)
        summary = inventory.get_inventory_summary()
        assert "cash_balance" in summary
        assert "total_cars" in summary
        assert summary["total_cars"] == 1
