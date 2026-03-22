"""White-box tests for the Dice module."""
from unittest.mock import patch
from moneypoly.dice import Dice


class TestDiceInit:
    """Test dice initialization."""

    def test_initial_values(self):
        d = Dice()
        assert d.die1 == 0
        assert d.die2 == 0
        assert d.doubles_streak == 0


class TestDiceRoll:
    """Test dice rolling logic and doubles tracking."""

    @patch("moneypoly.dice.random.randint", side_effect=[3, 4])
    def test_roll_non_doubles(self, _mock):
        d = Dice()
        total = d.roll()
        assert total == 7
        assert d.die1 == 3
        assert d.die2 == 4
        assert not d.is_doubles()
        assert d.doubles_streak == 0

    @patch("moneypoly.dice.random.randint", side_effect=[5, 5])
    def test_roll_doubles(self, _mock):
        d = Dice()
        total = d.roll()
        assert total == 10
        assert d.is_doubles()
        assert d.doubles_streak == 1

    @patch("moneypoly.dice.random.randint", side_effect=[2, 2, 3, 3, 4, 4])
    def test_consecutive_doubles(self, _mock):
        d = Dice()
        d.roll()
        assert d.doubles_streak == 1
        d.roll()
        assert d.doubles_streak == 2
        d.roll()
        assert d.doubles_streak == 3

    @patch("moneypoly.dice.random.randint", side_effect=[2, 2, 3, 5])
    def test_doubles_streak_resets_on_non_double(self, _mock):
        d = Dice()
        d.roll()
        assert d.doubles_streak == 1
        d.roll()
        assert d.doubles_streak == 0

    @patch("moneypoly.dice.random.randint", side_effect=[1, 1])
    def test_minimum_roll(self, _mock):
        d = Dice()
        assert d.roll() == 2

    @patch("moneypoly.dice.random.randint", side_effect=[6, 6])
    def test_maximum_roll(self, _mock):
        d = Dice()
        assert d.roll() == 12

    def test_roll_values_in_valid_range(self):
        """Each die should produce values between 1 and 6."""
        d = Dice()
        for _ in range(100):
            d.roll()
            assert 1 <= d.die1 <= 6
            assert 1 <= d.die2 <= 6
            assert 2 <= d.total() <= 12

    def test_reset(self):
        d = Dice()
        d.roll()
        d.reset()
        assert d.die1 == 0
        assert d.die2 == 0
        assert d.doubles_streak == 0

    @patch("moneypoly.dice.random.randint", side_effect=[3, 4])
    def test_describe(self, _mock):
        d = Dice()
        d.roll()
        assert d.describe() == "3 + 4 = 7"

    @patch("moneypoly.dice.random.randint", side_effect=[5, 5])
    def test_describe_doubles(self, _mock):
        d = Dice()
        d.roll()
        assert "(DOUBLES)" in d.describe()

    def test_repr(self):
        d = Dice()
        assert "Dice" in repr(d)
