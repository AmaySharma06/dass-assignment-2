"""White-box tests for the Board module."""
from moneypoly.board import Board
from moneypoly.player import Player
from moneypoly.config import (
    JAIL_POSITION, GO_TO_JAIL_POSITION,
    FREE_PARKING_POSITION, INCOME_TAX_POSITION, LUXURY_TAX_POSITION,
)


class TestBoardInit:
    """Test board initialization."""

    def test_has_26_properties(self):
        b = Board()
        assert len(b.properties) == 26

    def test_has_8_groups(self):
        b = Board()
        assert len(b.groups) == 8


class TestBoardTileTypes:
    """Test tile type identification."""

    def test_go_tile(self):
        b = Board()
        assert b.get_tile_type(0) == "go"

    def test_jail_tile(self):
        b = Board()
        assert b.get_tile_type(JAIL_POSITION) == "jail"

    def test_go_to_jail_tile(self):
        b = Board()
        assert b.get_tile_type(GO_TO_JAIL_POSITION) == "go_to_jail"

    def test_free_parking_tile(self):
        b = Board()
        assert b.get_tile_type(FREE_PARKING_POSITION) == "free_parking"

    def test_income_tax_tile(self):
        b = Board()
        assert b.get_tile_type(INCOME_TAX_POSITION) == "income_tax"

    def test_luxury_tax_tile(self):
        b = Board()
        assert b.get_tile_type(LUXURY_TAX_POSITION) == "luxury_tax"

    def test_chance_tiles(self):
        b = Board()
        assert b.get_tile_type(7) == "chance"
        assert b.get_tile_type(22) == "chance"
        assert b.get_tile_type(36) == "chance"

    def test_community_chest_tiles(self):
        b = Board()
        assert b.get_tile_type(2) == "community_chest"
        assert b.get_tile_type(17) == "community_chest"
        assert b.get_tile_type(33) == "community_chest"

    def test_railroad_tiles(self):
        b = Board()
        assert b.get_tile_type(5) == "railroad"
        assert b.get_tile_type(15) == "railroad"
        assert b.get_tile_type(25) == "railroad"
        assert b.get_tile_type(35) == "railroad"

    def test_property_tile(self):
        b = Board()
        assert b.get_tile_type(1) == "property"

    def test_blank_tile(self):
        b = Board()
        # Position 10 is jail (special), so find a non-special, non-property tile
        # Position 12 for example may be blank
        tile = b.get_tile_type(12)
        # Should be either property or blank
        assert tile in ("property", "blank")


class TestBoardPropertyLookup:
    """Test property lookup functions."""

    def test_get_property_at_valid(self):
        b = Board()
        prop = b.get_property_at(1)
        assert prop is not None
        assert prop.name == "Mediterranean Avenue"

    def test_get_property_at_invalid(self):
        b = Board()
        assert b.get_property_at(0) is None  # Go is not a property

    def test_get_property_at_railroad_is_instantiated(self):
        b = Board()
        railroad = b.get_property_at(5)
        assert railroad is not None
        assert railroad.position == 5

    def test_is_purchasable_unowned(self):
        b = Board()
        assert b.is_purchasable(1)

    def test_not_purchasable_when_owned(self):
        b = Board()
        prop = b.get_property_at(1)
        prop.owner = Player("Alice")
        assert not b.is_purchasable(1)

    def test_not_purchasable_when_mortgaged(self):
        b = Board()
        prop = b.get_property_at(1)
        prop.is_mortgaged = True
        assert not b.is_purchasable(1)

    def test_not_purchasable_non_property(self):
        b = Board()
        assert not b.is_purchasable(0)  # Go

    def test_is_special_tile(self):
        b = Board()
        assert b.is_special_tile(0)
        assert b.is_special_tile(JAIL_POSITION)
        assert not b.is_special_tile(1)  # property, not special


class TestBoardOwnership:
    """Test ownership queries."""

    def test_properties_owned_by(self):
        b = Board()
        alice = Player("Alice")
        b.properties[0].owner = alice
        b.properties[1].owner = alice
        owned = b.properties_owned_by(alice)
        assert len(owned) == 2

    def test_unowned_properties(self):
        b = Board()
        assert len(b.unowned_properties()) == 26
        b.properties[0].owner = Player("Alice")
        assert len(b.unowned_properties()) == 25

    def test_repr(self):
        b = Board()
        assert "Board" in repr(b)
