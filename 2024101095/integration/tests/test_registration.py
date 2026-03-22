"""
Integration Tests – Registration Module
========================================
Tests that the Registration module correctly registers members,
assigns IDs, and supports lookups.
"""
import pytest
from integration.code import Role, RegistrationModule


class TestRegistrationModule:
    """Test registration of new crew members."""

    def test_register_basic_member(self, registration):
        """Register a member with name only."""
        member = registration.register_member("Amay")
        assert member.member_id == 1
        assert member.name == "Amay"
        assert member.role is None
        assert member.is_available is True

    def test_register_member_with_role(self, registration):
        """Register member with an explicit role."""
        member = registration.register_member("Vikram", Role.DRIVER)
        assert member.role == Role.DRIVER

    def test_ids_are_unique_and_incrementing(self, registration):
        """Each new member gets a unique incrementing ID."""
        m1 = registration.register_member("A")
        m2 = registration.register_member("B")
        m3 = registration.register_member("C")
        assert m1.member_id == 1
        assert m2.member_id == 2
        assert m3.member_id == 3

    def test_get_member_by_id(self, registration):
        """Can retrieve a member by their ID."""
        member = registration.register_member("Dom", Role.DRIVER)
        fetched = registration.get_member(member.member_id)
        assert fetched is not None
        assert fetched.name == "Dom"

    def test_get_member_by_name_case_insensitive(self, registration):
        """Name lookup is case-insensitive."""
        registration.register_member("Letty", Role.DRIVER)
        assert registration.get_member_by_name("letty") is not None
        assert registration.get_member_by_name("LETTY") is not None

    def test_get_member_unknown_id_returns_none(self, registration):
        """Fetching a nonexistent ID returns None."""
        assert registration.get_member(999) is None

    def test_empty_name_raises_value_error(self, registration):
        """Registering with an empty name is not allowed."""
        with pytest.raises(ValueError, match="empty"):
            registration.register_member("")

    def test_whitespace_name_raises_value_error(self, registration):
        """Registering with only whitespace is not allowed."""
        with pytest.raises(ValueError):
            registration.register_member("   ")

    def test_member_count_increases(self, registration):
        """Count increments after each registration."""
        assert registration.count() == 0
        registration.register_member("X")
        assert registration.count() == 1
        registration.register_member("Y")
        assert registration.count() == 2

    def test_remove_member(self, registration):
        """Removing a member decreases count and makes them unfindable."""
        member = registration.register_member("Temp")
        assert registration.remove_member(member.member_id) is True
        assert registration.get_member(member.member_id) is None
        assert registration.count() == 0

    def test_remove_nonexistent_member(self, registration):
        """Removing a member that doesn't exist returns False."""
        assert registration.remove_member(999) is False

    def test_duplicate_names_get_different_ids(self, registration):
        """Two members with the same name get different IDs."""
        m1 = registration.register_member("Brian", Role.DRIVER)
        m2 = registration.register_member("Brian", Role.MECHANIC)
        assert m1.member_id != m2.member_id

    def test_is_registered_check(self, registration):
        """is_registered returns correct boolean."""
        member = registration.register_member("Check")
        assert registration.is_registered(member.member_id) is True
        assert registration.is_registered(999) is False

    def test_get_all_members(self, registration):
        """get_all_members returns every registered member."""
        registration.register_member("Alpha")
        registration.register_member("Beta")
        all_members = registration.get_all_members()
        assert len(all_members) == 2
        names = {m.name for m in all_members}
        assert names == {"Alpha", "Beta"}
