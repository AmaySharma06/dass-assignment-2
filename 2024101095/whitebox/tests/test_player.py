"""White-box tests for the Player module."""
import pytest
from moneypoly.player import Player
from moneypoly.config import STARTING_BALANCE, BOARD_SIZE, GO_SALARY, JAIL_POSITION


class TestPlayerInit:
    """Test player initialization."""

    def test_default_balance(self):
        p = Player("Alice")
        assert p.balance == STARTING_BALANCE

    def test_custom_balance(self):
        p = Player("Bob", balance=500)
        assert p.balance == 500

    def test_initial_position(self):
        p = Player("Alice")
        assert p.position == 0

    def test_initial_state(self):
        p = Player("Alice")
        assert not p.jail_info["in_jail"]
        assert p.jail_info["jail_turns"] == 0
        assert p.jail_info["get_out_of_jail_cards"] == 0
        assert not p.is_eliminated
        assert p.properties == []


class TestPlayerMoney:
    """Test money operations."""

    def test_add_money(self):
        p = Player("Alice", balance=100)
        p.add_money(50)
        assert p.balance == 150

    def test_add_zero(self):
        p = Player("Alice", balance=100)
        p.add_money(0)
        assert p.balance == 100

    def test_add_negative_raises(self):
        p = Player("Alice")
        with pytest.raises(ValueError):
            p.add_money(-10)

    def test_deduct_money(self):
        p = Player("Alice", balance=100)
        p.deduct_money(30)
        assert p.balance == 70

    def test_deduct_zero(self):
        p = Player("Alice", balance=100)
        p.deduct_money(0)
        assert p.balance == 100

    def test_deduct_negative_raises(self):
        p = Player("Alice")
        with pytest.raises(ValueError):
            p.deduct_money(-10)

    def test_deduct_more_than_balance(self):
        p = Player("Alice", balance=50)
        p.deduct_money(100)
        assert p.balance == -50


class TestPlayerBankruptcy:
    """Test bankruptcy detection."""

    def test_not_bankrupt_positive_balance(self):
        p = Player("Alice", balance=100)
        assert not p.is_bankrupt()

    def test_bankrupt_at_zero(self):
        p = Player("Alice", balance=0)
        assert p.is_bankrupt()

    def test_bankrupt_negative(self):
        p = Player("Alice", balance=-50)
        assert p.is_bankrupt()


class TestPlayerMovement:
    """Test movement and Go salary."""

    def test_basic_move(self):
        p = Player("Alice")
        pos = p.move(5)
        assert pos == 5
        assert p.position == 5

    def test_wrap_around_board(self):
        p = Player("Alice")
        p.position = 38
        pos = p.move(4)
        assert pos == 2
        # Should have passed Go and collected salary
        assert p.balance == STARTING_BALANCE + GO_SALARY

    def test_land_on_go(self):
        p = Player("Alice")
        p.position = BOARD_SIZE - 5
        pos = p.move(5)
        assert pos == 0
        assert p.balance == STARTING_BALANCE + GO_SALARY

    def test_no_go_salary_without_passing(self):
        p = Player("Alice")
        p.position = 5
        p.move(3)
        assert p.balance == STARTING_BALANCE

    def test_move_zero_steps(self):
        p = Player("Alice")
        p.position = 10
        pos = p.move(0)
        assert pos == 10


class TestPlayerJail:
    """Test jail mechanics."""

    def test_go_to_jail(self):
        p = Player("Alice")
        p.position = 30
        p.go_to_jail()
        assert p.position == JAIL_POSITION
        assert p.jail_info["in_jail"]
        assert p.jail_info["jail_turns"] == 0

    def test_go_to_jail_resets_turns(self):
        p = Player("Alice")
        p.jail_info["jail_turns"] = 2
        p.go_to_jail()
        assert p.jail_info["jail_turns"] == 0


class TestPlayerProperties:
    """Test property management."""

    def test_add_property(self):
        p = Player("Alice")
        p.add_property("prop1")
        assert "prop1" in p.properties

    def test_add_duplicate_property(self):
        p = Player("Alice")
        p.add_property("prop1")
        p.add_property("prop1")
        assert len(p.properties) == 1

    def test_remove_property(self):
        p = Player("Alice")
        p.add_property("prop1")
        p.remove_property("prop1")
        assert "prop1" not in p.properties

    def test_remove_nonexistent_property(self):
        p = Player("Alice")
        p.remove_property("prop1")  # should not raise

    def test_count_properties(self):
        p = Player("Alice")
        assert p.count_properties() == 0
        p.add_property("a")
        p.add_property("b")
        assert p.count_properties() == 2


class TestPlayerNetWorth:
    """Test net worth calculation (includes property values)."""

    def test_net_worth_no_properties(self):
        p = Player("Alice", balance=500)
        assert p.net_worth() == 500

    def test_net_worth_with_properties(self):
        from moneypoly.property import Property
        p = Player("Alice", balance=500)
        prop = Property("Test", 1, {"price": 200, "base_rent": 10})
        prop.owner = p
        p.add_property(prop)
        assert p.net_worth() == 700  # 500 + 200


class TestPlayerDisplay:
    """Test display methods."""

    def test_status_line(self):
        p = Player("Alice")
        line = p.status_line()
        assert "Alice" in line
        assert str(STARTING_BALANCE) in line

    def test_status_line_jailed(self):
        p = Player("Alice")
        p.jail_info["in_jail"] = True
        assert "[JAILED]" in p.status_line()

    def test_repr(self):
        p = Player("Alice")
        assert "Alice" in repr(p)
