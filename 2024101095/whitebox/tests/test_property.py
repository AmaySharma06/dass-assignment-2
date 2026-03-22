"""White-box tests for the Property and PropertyGroup modules."""
from moneypoly.property import Property, PropertyGroup
from moneypoly.player import Player


class TestPropertyInit:
    """Test property initialization."""

    def test_basic_creation(self):
        p = Property("Test Ave", 1, {"price": 100, "base_rent": 10})
        assert p.name == "Test Ave"
        assert p.position == 1
        assert p.economics["price"] == 100
        assert p.economics["base_rent"] == 10
        assert p.mortgage_value == 50
        assert p.owner is None
        assert not p.is_mortgaged
        assert p.buildings["houses"] == 0

    def test_with_group(self):
        g = PropertyGroup("Brown", "brown")
        p = Property("Test Ave", 1, {"price": 100, "base_rent": 10}, group=g)
        assert p.group == g
        assert p in g.properties

    def test_no_duplicate_group_registration(self):
        g = PropertyGroup("Brown", "brown")
        p = Property("Test Ave", 1, {"price": 100, "base_rent": 10}, group=g)
        # Adding again shouldn't duplicate
        p2 = Property("Test2", 2, {"price": 100, "base_rent": 10}, group=g)
        assert len(g.properties) == 2


class TestPropertyRent:
    """Test rent calculation."""

    def test_base_rent(self):
        p = Property("Test Ave", 1, {"price": 100, "base_rent": 10})
        player = Player("Alice")
        p.owner = player
        assert p.get_rent() == 10

    def test_rent_doubled_with_full_group(self):
        g = PropertyGroup("Brown", "brown")
        p1 = Property("Ave1", 1, {"price": 60, "base_rent": 2}, group=g)
        p2 = Property("Ave2", 3, {"price": 60, "base_rent": 4}, group=g)
        player = Player("Alice")
        p1.owner = player
        p2.owner = player
        assert p1.get_rent() == 4  # 2 * 2
        assert p2.get_rent() == 8  # 4 * 2

    def test_rent_not_doubled_partial_group(self):
        g = PropertyGroup("Brown", "brown")
        p1 = Property("Ave1", 1, {"price": 60, "base_rent": 2}, group=g)
        p2 = Property("Ave2", 3, {"price": 60, "base_rent": 4}, group=g)
        alice = Player("Alice")
        bob = Player("Bob")
        p1.owner = alice
        p2.owner = bob
        assert p1.get_rent() == 2  # not doubled

    def test_rent_zero_when_mortgaged(self):
        p = Property("Test Ave", 1, {"price": 100, "base_rent": 10})
        player = Player("Alice")
        p.owner = player
        p.mortgage()
        assert p.get_rent() == 0


class TestPropertyMortgage:
    """Test mortgage and unmortgage."""

    def test_mortgage_returns_half_price(self):
        p = Property("Test Ave", 1, {"price": 100, "base_rent": 10})
        payout = p.mortgage()
        assert payout == 50
        assert p.is_mortgaged

    def test_mortgage_already_mortgaged(self):
        p = Property("Test Ave", 1, {"price": 100, "base_rent": 10})
        p.mortgage()
        assert p.mortgage() == 0

    def test_unmortgage_returns_cost(self):
        p = Property("Test Ave", 1, {"price": 100, "base_rent": 10})
        p.mortgage()
        cost = p.unmortgage()
        assert cost == 55  # 50 * 1.1
        assert not p.is_mortgaged

    def test_unmortgage_not_mortgaged(self):
        p = Property("Test Ave", 1, {"price": 100, "base_rent": 10})
        assert p.unmortgage() == 0

    def test_is_available(self):
        p = Property("Test Ave", 1, {"price": 100, "base_rent": 10})
        assert p.is_available()
        player = Player("Alice")
        p.owner = player
        assert not p.is_available()

    def test_is_available_mortgaged(self):
        p = Property("Test Ave", 1, {"price": 100, "base_rent": 10})
        p.is_mortgaged = True
        assert not p.is_available()


class TestPropertyGroup:
    """Test PropertyGroup behavior."""

    def test_all_owned_by_single_owner(self):
        g = PropertyGroup("Brown", "brown")
        p1 = Property("A", 1, {"price": 60, "base_rent": 2}, group=g)
        p2 = Property("B", 3, {"price": 60, "base_rent": 4}, group=g)
        alice = Player("Alice")
        p1.owner = alice
        p2.owner = alice
        assert g.all_owned_by(alice)

    def test_all_owned_by_fails_with_mixed_owners(self):
        g = PropertyGroup("Brown", "brown")
        p1 = Property("A", 1, {"price": 60, "base_rent": 2}, group=g)
        p2 = Property("B", 3, {"price": 60, "base_rent": 4}, group=g)
        alice = Player("Alice")
        bob = Player("Bob")
        p1.owner = alice
        p2.owner = bob
        assert not g.all_owned_by(alice)
        assert not g.all_owned_by(bob)

    def test_all_owned_by_none_returns_false(self):
        g = PropertyGroup("Brown", "brown")
        Property("A", 1, {"price": 60, "base_rent": 2}, group=g)
        assert not g.all_owned_by(None)

    def test_all_owned_by_partial_unowned(self):
        g = PropertyGroup("Brown", "brown")
        p1 = Property("A", 1, {"price": 60, "base_rent": 2}, group=g)
        Property("B", 3, {"price": 60, "base_rent": 4}, group=g)
        alice = Player("Alice")
        p1.owner = alice
        assert not g.all_owned_by(alice)

    def test_get_owner_counts(self):
        g = PropertyGroup("Brown", "brown")
        p1 = Property("A", 1, {"price": 60, "base_rent": 2}, group=g)
        p2 = Property("B", 3, {"price": 60, "base_rent": 4}, group=g)
        alice = Player("Alice")
        p1.owner = alice
        p2.owner = alice
        counts = g.get_owner_counts()
        assert counts[alice] == 2

    def test_size(self):
        g = PropertyGroup("Brown", "brown")
        Property("A", 1, {"price": 60, "base_rent": 2}, group=g)
        Property("B", 3, {"price": 60, "base_rent": 4}, group=g)
        assert g.size() == 2

    def test_add_property(self):
        g = PropertyGroup("Brown", "brown")
        p = Property("A", 1, {"price": 60, "base_rent": 2})
        g.add_property(p)
        assert p in g.properties
        assert p.group == g

    def test_repr(self):
        g = PropertyGroup("Brown", "brown")
        assert "Brown" in repr(g)

    def test_property_repr(self):
        p = Property("Test", 1, {"price": 100, "base_rent": 10})
        assert "unowned" in repr(p)
        player = Player("Alice")
        p.owner = player
        assert "Alice" in repr(p)
