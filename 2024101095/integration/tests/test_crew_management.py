"""
Integration Tests – Crew Management Module
============================================
Tests how Crew Management integrates with Registration:
registration changes must be visible to crew management.
"""
import pytest
from integration.code import (
    Role, MemberNotFoundError, CrewManagementModule
)


class TestCrewManagementIntegration:
    """Crew Management uses Registration as a shared data source."""

    def test_registered_members_visible_via_crew(self, crew_management):
        """Members added through registration appear in crew queries."""
        crew_management._registration.register_member("Alice", Role.DRIVER)
        drivers = crew_management.get_members_by_role(Role.DRIVER)
        assert len(drivers) == 1
        assert drivers[0].name == "Alice"

    def test_multiple_roles_correctly_separated(self, crew_management):
        """Members with different roles appear in the right buckets."""
        crew_management._registration.register_member("Alice", Role.DRIVER)
        crew_management._registration.register_member("Bob", Role.MECHANIC)
        crew_management._registration.register_member("Carol", Role.NAVIGATOR)

        assert len(crew_management.get_members_by_role(Role.DRIVER)) == 1
        assert len(crew_management.get_members_by_role(Role.MECHANIC)) == 1
        assert len(crew_management.get_members_by_role(Role.NAVIGATOR)) == 1
        assert len(crew_management.get_members_by_role(Role.STRATEGIST)) == 0

    def test_assign_role_after_registration(self, crew_management):
        """A member registered without role can be given one later."""
        member = crew_management._registration.register_member("Dave")
        assert member.role is None

        updated = crew_management.assign_role(member.member_id, Role.STRATEGIST)
        assert updated.role == Role.STRATEGIST

    def test_assign_role_to_unknown_member_raises(self, crew_management):
        """Assigning a role to a non-existent member raises MemberNotFoundError."""
        with pytest.raises(MemberNotFoundError):
            crew_management.assign_role(999, Role.DRIVER)

    def test_skill_level_update(self, crew_management):
        """Skill level can be updated within the 1-10 range."""
        member = crew_management._registration.register_member("Eva", Role.DRIVER)
        crew_management.update_skill_level(member.member_id, 8)
        assert member.skill_level == 8

    def test_skill_level_out_of_range_raises(self, crew_management):
        """Skill level outside 1-10 raises ValueError."""
        member = crew_management._registration.register_member("Frank", Role.MECHANIC)
        with pytest.raises(ValueError):
            crew_management.update_skill_level(member.member_id, 11)
        with pytest.raises(ValueError):
            crew_management.update_skill_level(member.member_id, 0)

    def test_availability_filtering(self, crew_management):
        """Unavailable members are excluded from available-role queries."""
        m1 = crew_management._registration.register_member("G", Role.DRIVER)
        m2 = crew_management._registration.register_member("H", Role.DRIVER)

        m1.is_available = False

        available = crew_management.get_available_by_role(Role.DRIVER)
        assert len(available) == 1
        assert available[0].member_id == m2.member_id

    def test_has_available_role(self, crew_management):
        """has_available_role reflects current availability correctly."""
        assert crew_management.has_available_role(Role.DRIVER) is False

        driver = crew_management._registration.register_member("I", Role.DRIVER)
        assert crew_management.has_available_role(Role.DRIVER) is True

        driver.is_available = False
        assert crew_management.has_available_role(Role.DRIVER) is False

    def test_set_availability_via_module(self, crew_management):
        """set_availability updates the member's availability flag."""
        member = crew_management._registration.register_member("J", Role.PIT_CREW)
        crew_management.set_availability(member.member_id, False)
        assert member.is_available is False

        crew_management.set_availability(member.member_id, True)
        assert member.is_available is True

    def test_get_best_driver_picks_highest_skill(self, crew_management):
        """get_best_driver returns the available driver with the most skill."""
        reg = crew_management._registration
        m1 = reg.register_member("Low Skill", Role.DRIVER)
        m2 = reg.register_member("High Skill", Role.DRIVER)

        crew_management.update_skill_level(m1.member_id, 3)
        crew_management.update_skill_level(m2.member_id, 9)

        best = crew_management.get_best_driver()
        assert best is not None
        assert best.member_id == m2.member_id

    def test_create_team(self, crew_management):
        """create_team stores the team and retrieve it back."""
        reg = crew_management._registration
        m1 = reg.register_member("K", Role.DRIVER)
        m2 = reg.register_member("L", Role.MECHANIC)

        team = crew_management.create_team("Alpha", [m1.member_id, m2.member_id])
        assert len(team) == 2

        fetched = crew_management.get_team("Alpha")
        assert fetched is not None
        member_ids = {m.member_id for m in fetched}
        assert m1.member_id in member_ids
        assert m2.member_id in member_ids
