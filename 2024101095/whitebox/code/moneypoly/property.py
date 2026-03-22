"""Module docstring"""
# pylint: disable=import-error
class Property:
    """Represents a single purchasable property tile on the MoneyPoly board."""

    FULL_GROUP_MULTIPLIER = 2

    def __init__(self, name, position, economics, group=None):
        self.name = name
        self.position = position
        self.economics = economics
        self.owner = None
        self.is_mortgaged = False
        self.buildings = {"houses": 0, "hotel": 0}

        # Register with the group immediately on creation
        self.group = group
        if group is not None and self not in group.properties:
            group.properties.append(self)

    @property
    def mortgage_value(self):
        """Calculate the mortgage value."""
        return self.economics.get("price", 0) // 2

    def get_rent(self):
        """
        Return the rent owed for landing on this property.
        Rent is doubled if the owner holds the entire colour group.
        Returns 0 if the property is mortgaged.
        """
        if self.is_mortgaged:
            return 0
        if self.group is not None and self.group.all_owned_by(self.owner):
            return self.economics.get("base_rent", 0) * self.FULL_GROUP_MULTIPLIER
        return self.economics.get("base_rent", 0)

    def mortgage(self):
        """
        Mortgage this property and return the payout to the owner.
        Returns 0 if already mortgaged.
        """
        if self.is_mortgaged:
            return 0
        self.is_mortgaged = True
        return self.mortgage_value

    def unmortgage(self):
        """
        Lift the mortgage on this property.
        Returns the cost (110 % of mortgage value), or 0 if not mortgaged.
        """
        if not self.is_mortgaged:
            return 0

        cost = int(self.mortgage_value * 1.1)
        self.is_mortgaged = False
        return cost

    def is_available(self):
        """Return True if this property can be purchased (unowned, not mortgaged)."""
        return self.owner is None and not self.is_mortgaged

    def __repr__(self):
        owner_name = self.owner.name if self.owner else "unowned"
        return f"Property({self.name!r}, pos={self.position}, owner={owner_name!r})"


class PropertyGroup:
    """Class representing a property group/color set."""
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.properties = []

    def add_property(self, prop):
        """Add a Property to this group and back-link it."""
        if prop not in self.properties:
            self.properties.append(prop)
            prop.group = self

    def all_owned_by(self, player):
        """Return True if every property in this group is owned by `player`."""
        if player is None:
            return False
        return any(p.owner == player for p in self.properties)

    def get_owner_counts(self):
        """Return a dict mapping each owner to how many properties they hold in this group."""
        counts = {}
        for prop in self.properties:
            if prop.owner is not None:
                counts[prop.owner] = counts.get(prop.owner, 0) + 1
        return counts

    def size(self):
        """Return the number of properties in this group."""
        return len(self.properties)

    def __repr__(self):
        return f"PropertyGroup({self.name!r}, {len(self.properties)} properties)"
