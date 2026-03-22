"""
Inventory Module
================
Tracks cars, spare parts, tools, and cash balance.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class CarCondition(Enum):
    """Condition states for vehicles."""
    PERFECT = "perfect"
    GOOD = "good"
    DAMAGED = "damaged"
    TOTALED = "totaled"


@dataclass
class Car:
    """Represents a vehicle in the inventory."""
    car_id: int
    name: str
    model: str
    horsepower: int
    condition: CarCondition = CarCondition.GOOD
    is_available: bool = True

    def needs_repair(self) -> bool:
        """Check if the car needs repair."""
        return self.condition in (CarCondition.DAMAGED, CarCondition.TOTALED)

    def __hash__(self):
        return hash(self.car_id)


@dataclass
class SparePart:
    """Represents a spare part in inventory."""
    part_id: int
    name: str
    quantity: int
    unit_cost: float


@dataclass
class Tool:
    """Represents a tool in inventory."""
    tool_id: int
    name: str
    is_available: bool = True


class InsufficientFundsError(Exception):
    """Raised when there's not enough cash for an operation."""
    pass


class ItemNotFoundError(Exception):
    """Raised when an inventory item is not found."""
    pass


class InventoryModule:
    """
    Manages the garage inventory including cars, parts, tools, and finances.
    """

    def __init__(self, initial_balance: float = 0.0):
        self._cash_balance: float = initial_balance
        self._cars: Dict[int, Car] = {}
        self._parts: Dict[int, SparePart] = {}
        self._tools: Dict[int, Tool] = {}
        self._next_car_id: int = 1
        self._next_part_id: int = 1
        self._next_tool_id: int = 1

    # --- Cash Management ---

    def get_balance(self) -> float:
        """Get current cash balance."""
        return self._cash_balance

    def add_funds(self, amount: float) -> float:
        """
        Add funds to the balance.

        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self._cash_balance += amount
        return self._cash_balance

    def deduct_funds(self, amount: float) -> float:
        """
        Deduct funds from the balance.

        Raises:
            ValueError: If amount is not positive
            InsufficientFundsError: If balance is insufficient
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > self._cash_balance:
            raise InsufficientFundsError(
                f"Insufficient funds: need ${amount}, have ${self._cash_balance}"
            )
        self._cash_balance -= amount
        return self._cash_balance

    # --- Car Management ---

    def add_car(self, name: str, model: str, horsepower: int,
                condition: CarCondition = CarCondition.GOOD) -> Car:
        """Add a new car to the inventory."""
        car = Car(
            car_id=self._next_car_id,
            name=name,
            model=model,
            horsepower=horsepower,
            condition=condition
        )
        self._cars[self._next_car_id] = car
        self._next_car_id += 1
        return car

    def get_car(self, car_id: int) -> Optional[Car]:
        """Get a car by ID."""
        return self._cars.get(car_id)

    def get_all_cars(self) -> List[Car]:
        """Get all cars."""
        return list(self._cars.values())

    def get_available_cars(self) -> List[Car]:
        """Get all available (not in use and not totaled) cars."""
        return [
            c for c in self._cars.values()
            if c.is_available and c.condition != CarCondition.TOTALED
        ]

    def get_race_ready_cars(self) -> List[Car]:
        """Get cars that are ready for racing (good condition)."""
        return [
            c for c in self._cars.values()
            if c.is_available and c.condition in (CarCondition.PERFECT, CarCondition.GOOD)
        ]

    def set_car_availability(self, car_id: int, available: bool) -> Car:
        """Set a car's availability status."""
        car = self._cars.get(car_id)
        if car is None:
            raise ItemNotFoundError(f"Car with ID {car_id} not found")
        car.is_available = available
        return car

    def set_car_condition(self, car_id: int, condition: CarCondition) -> Car:
        """Update a car's condition."""
        car = self._cars.get(car_id)
        if car is None:
            raise ItemNotFoundError(f"Car with ID {car_id} not found")
        car.condition = condition
        return car

    def repair_car(self, car_id: int, repair_cost: float) -> Car:
        """
        Repair a damaged car.

        Raises:
            ItemNotFoundError: If car not found
            InsufficientFundsError: If can't afford repair
        """
        car = self._cars.get(car_id)
        if car is None:
            raise ItemNotFoundError(f"Car with ID {car_id} not found")
        if car.condition == CarCondition.TOTALED:
            raise ValueError("Totaled cars cannot be repaired")
        self.deduct_funds(repair_cost)
        car.condition = CarCondition.GOOD
        return car

    # --- Parts Management ---

    def add_part(self, name: str, quantity: int, unit_cost: float) -> SparePart:
        """Add a spare part to inventory."""
        part = SparePart(
            part_id=self._next_part_id,
            name=name,
            quantity=quantity,
            unit_cost=unit_cost
        )
        self._parts[self._next_part_id] = part
        self._next_part_id += 1
        return part

    def get_part(self, part_id: int) -> Optional[SparePart]:
        """Get a part by ID."""
        return self._parts.get(part_id)

    def use_parts(self, part_id: int, quantity: int) -> SparePart:
        """Use some quantity of a part."""
        part = self._parts.get(part_id)
        if part is None:
            raise ItemNotFoundError(f"Part with ID {part_id} not found")
        if quantity > part.quantity:
            raise ValueError(f"Not enough parts: need {quantity}, have {part.quantity}")
        part.quantity -= quantity
        return part

    # --- Tools Management ---

    def add_tool(self, name: str) -> Tool:
        """Add a tool to inventory."""
        tool = Tool(tool_id=self._next_tool_id, name=name)
        self._tools[self._next_tool_id] = tool
        self._next_tool_id += 1
        return tool

    def get_tool(self, tool_id: int) -> Optional[Tool]:
        """Get a tool by ID."""
        return self._tools.get(tool_id)

    def get_available_tools(self) -> List[Tool]:
        """Get all available tools."""
        return [t for t in self._tools.values() if t.is_available]

    # --- Summary ---

    def get_inventory_summary(self) -> dict:
        """Get a summary of the inventory."""
        return {
            "cash_balance": self._cash_balance,
            "total_cars": len(self._cars),
            "available_cars": len(self.get_available_cars()),
            "race_ready_cars": len(self.get_race_ready_cars()),
            "total_parts": sum(p.quantity for p in self._parts.values()),
            "total_tools": len(self._tools),
        }
