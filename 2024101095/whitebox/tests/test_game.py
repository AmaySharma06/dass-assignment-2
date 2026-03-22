"""White-box tests for the Game module - core game logic."""
from unittest.mock import patch, MagicMock
import pytest
from moneypoly.game import Game
from moneypoly.player import Player
from moneypoly.property import Property, PropertyGroup
from moneypoly.config import STARTING_BALANCE, JAIL_FINE, INCOME_TAX_AMOUNT, LUXURY_TAX_AMOUNT


class TestGameInit:
    """Test game initialization."""

    def test_creates_players(self):
        g = Game(["Alice", "Bob"])
        assert len(g.players) == 2
        assert g.players[0].name == "Alice"
        assert g.players[1].name == "Bob"

    def test_initializes_state(self):
        g = Game(["Alice", "Bob"])
        assert g.state["current_index"] == 0
        assert g.state["turn_number"] == 0
        assert g.state["running"]

    def test_creates_board(self):
        g = Game(["Alice", "Bob"])
        assert g.board is not None

    def test_creates_bank(self):
        g = Game(["Alice", "Bob"])
        assert g.bank is not None

    def test_creates_decks(self):
        g = Game(["Alice", "Bob"])
        assert g.decks["chance"] is not None
        assert g.decks["community_chest"] is not None


class TestGameTurnManagement:
    """Test turn management."""

    def test_current_player(self):
        g = Game(["Alice", "Bob"])
        assert g.current_player().name == "Alice"

    def test_advance_turn(self):
        g = Game(["Alice", "Bob"])
        g.advance_turn()
        assert g.current_player().name == "Bob"
        assert g.state["turn_number"] == 1

    def test_advance_turn_wraps(self):
        g = Game(["Alice", "Bob"])
        g.advance_turn()
        g.advance_turn()
        assert g.current_player().name == "Alice"


class TestGameBuyProperty:
    """Test property purchase."""

    def test_successful_purchase(self):
        g = Game(["Alice", "Bob"])
        player = g.current_player()
        prop = g.board.get_property_at(1)  # Mediterranean Ave, $60
        result = g.buy_property(player, prop)
        assert result
        assert prop.owner == player
        assert player.balance == STARTING_BALANCE - 60
        assert prop in player.properties

    def test_cannot_afford(self):
        g = Game(["Alice", "Bob"])
        player = g.current_player()
        player.balance = 50
        prop = g.board.get_property_at(1)  # $60
        result = g.buy_property(player, prop)
        assert not result
        assert prop.owner is None

    def test_exact_balance_can_buy(self):
        g = Game(["Alice", "Bob"])
        player = g.current_player()
        player.balance = 60
        prop = g.board.get_property_at(1)
        result = g.buy_property(player, prop)
        assert result
        assert player.balance == 0


class TestGamePayRent:
    """Test rent payment."""

    def test_pays_rent_to_owner(self):
        g = Game(["Alice", "Bob"])
        alice = g.players[0]
        bob = g.players[1]
        prop = g.board.get_property_at(1)  # rent = 2
        prop.owner = bob
        bob.add_property(prop)

        initial_alice = alice.balance
        initial_bob = bob.balance
        g.pay_rent(alice, prop)

        assert alice.balance == initial_alice - 2
        assert bob.balance == initial_bob + 2

    def test_no_rent_on_mortgaged(self):
        g = Game(["Alice", "Bob"])
        alice = g.players[0]
        bob = g.players[1]
        prop = g.board.get_property_at(1)
        prop.owner = bob
        prop.mortgage()

        initial = alice.balance
        g.pay_rent(alice, prop)
        assert alice.balance == initial

    def test_no_rent_if_unowned(self):
        g = Game(["Alice", "Bob"])
        alice = g.players[0]
        prop = g.board.get_property_at(1)
        initial = alice.balance
        g.pay_rent(alice, prop)
        assert alice.balance == initial


class TestGameMortgage:
    """Test mortgage operations."""

    def test_mortgage_property(self):
        g = Game(["Alice", "Bob"])
        player = g.players[0]
        prop = g.board.get_property_at(1)  # price 60, mortgage 30
        prop.owner = player
        player.add_property(prop)

        initial = player.balance
        initial_bank = g.bank.get_balance()
        result = g.mortgage_property(player, prop)
        assert result
        assert prop.is_mortgaged
        assert player.balance == initial + 30
        assert g.bank.get_balance() == initial_bank - 30

    def test_cannot_mortgage_others_property(self):
        g = Game(["Alice", "Bob"])
        alice = g.players[0]
        bob = g.players[1]
        prop = g.board.get_property_at(1)
        prop.owner = bob

        result = g.mortgage_property(alice, prop)
        assert not result

    def test_cannot_mortgage_already_mortgaged(self):
        g = Game(["Alice", "Bob"])
        player = g.players[0]
        prop = g.board.get_property_at(1)
        prop.owner = player
        player.add_property(prop)
        prop.mortgage()

        result = g.mortgage_property(player, prop)
        assert not result

    def test_mortgage_does_not_use_negative_bank_collect(self):
        """Regression for bug 11: mortgage flow should not call collect with negatives."""
        g = Game(["Alice", "Bob"])
        player = g.players[0]
        prop = g.board.get_property_at(1)
        prop.owner = player
        player.add_property(prop)
        g.bank.collect = MagicMock(wraps=g.bank.collect)

        g.mortgage_property(player, prop)

        for call in g.bank.collect.call_args_list:
            assert call.args[0] >= 0


class TestGameUnmortgage:
    """Test unmortgaging."""

    def test_unmortgage_property(self):
        g = Game(["Alice", "Bob"])
        player = g.players[0]
        prop = g.board.get_property_at(1)  # mortgage 30, unmortgage cost 33
        prop.owner = player
        player.add_property(prop)
        prop.mortgage()

        initial = player.balance
        result = g.unmortgage_property(player, prop)
        assert result
        assert not prop.is_mortgaged
        assert player.balance == initial - 33

    def test_cannot_unmortgage_not_owned(self):
        g = Game(["Alice", "Bob"])
        alice = g.players[0]
        bob = g.players[1]
        prop = g.board.get_property_at(1)
        prop.owner = bob
        prop.mortgage()

        result = g.unmortgage_property(alice, prop)
        assert not result

    def test_cannot_afford_unmortgage(self):
        g = Game(["Alice", "Bob"])
        player = g.players[0]
        player.balance = 10
        prop = g.board.get_property_at(1)  # cost 33
        prop.owner = player
        player.add_property(prop)
        prop.mortgage()

        result = g.unmortgage_property(player, prop)
        assert not result
        assert prop.is_mortgaged


class TestGameTrade:
    """Test property trading."""

    def test_successful_trade(self):
        g = Game(["Alice", "Bob"])
        alice = g.players[0]
        bob = g.players[1]
        prop = g.board.get_property_at(1)
        prop.owner = alice
        alice.add_property(prop)

        alice_initial = alice.balance
        bob_initial = bob.balance
        result = g.trade(alice, bob, prop, 100)

        assert result
        assert prop.owner == bob
        assert prop in bob.properties
        assert prop not in alice.properties
        assert alice.balance == alice_initial + 100
        assert bob.balance == bob_initial - 100

    def test_trade_fails_not_owner(self):
        g = Game(["Alice", "Bob"])
        alice = g.players[0]
        bob = g.players[1]
        prop = g.board.get_property_at(1)
        prop.owner = bob

        result = g.trade(alice, bob, prop, 100)
        assert not result

    def test_trade_fails_cannot_afford(self):
        g = Game(["Alice", "Bob"])
        alice = g.players[0]
        bob = g.players[1]
        bob.balance = 50
        prop = g.board.get_property_at(1)
        prop.owner = alice
        alice.add_property(prop)

        result = g.trade(alice, bob, prop, 100)
        assert not result


class TestGameFindWinner:
    """Test winner determination."""

    def test_find_winner_highest_net_worth(self):
        g = Game(["Alice", "Bob"])
        g.players[0].balance = 1000
        g.players[1].balance = 2000
        winner = g.find_winner()
        assert winner.name == "Bob"

    def test_find_winner_with_properties(self):
        g = Game(["Alice", "Bob"])
        alice = g.players[0]
        bob = g.players[1]
        alice.balance = 500
        bob.balance = 400
        prop = g.board.get_property_at(39)  # Boardwalk, $400
        prop.owner = bob
        bob.add_property(prop)
        # Alice: 500, Bob: 400 + 400 = 800
        winner = g.find_winner()
        assert winner.name == "Bob"

    def test_find_winner_no_players(self):
        g = Game(["Alice", "Bob"])
        g.players.clear()
        assert g.find_winner() is None


class TestGameBankruptcy:
    """Test bankruptcy handling."""

    def test_check_bankruptcy_eliminates_player(self):
        g = Game(["Alice", "Bob"])
        alice = g.players[0]
        alice.balance = 0
        g._check_bankruptcy(alice)
        assert alice not in g.players
        assert alice.is_eliminated

    def test_bankruptcy_releases_properties(self):
        g = Game(["Alice", "Bob"])
        alice = g.players[0]
        prop = g.board.get_property_at(1)
        prop.owner = alice
        alice.add_property(prop)
        alice.balance = 0

        g._check_bankruptcy(alice)
        assert prop.owner is None
        assert not prop.is_mortgaged


class TestGameApplyCard:
    """Test card effect application."""

    def test_collect_card(self):
        g = Game(["Alice", "Bob"])
        player = g.current_player()
        initial = player.balance
        card = {"description": "Test", "action": "collect", "value": 50}
        g._apply_card(player, card)
        assert player.balance == initial + 50

    def test_pay_card(self):
        g = Game(["Alice", "Bob"])
        player = g.current_player()
        initial = player.balance
        card = {"description": "Test", "action": "pay", "value": 50}
        g._apply_card(player, card)
        assert player.balance == initial - 50

    def test_jail_card(self):
        g = Game(["Alice", "Bob"])
        player = g.current_player()
        card = {"description": "Test", "action": "jail", "value": 0}
        g._apply_card(player, card)
        assert player.jail_info["in_jail"]

    def test_jail_free_card(self):
        g = Game(["Alice", "Bob"])
        player = g.current_player()
        card = {"description": "Test", "action": "jail_free", "value": 0}
        g._apply_card(player, card)
        assert player.jail_info["get_out_of_jail_cards"] == 1

    def test_null_card(self):
        g = Game(["Alice", "Bob"])
        player = g.current_player()
        initial = player.balance
        g._apply_card(player, None)
        assert player.balance == initial  # no effect

    def test_birthday_card_collects_from_poor_players_too(self):
        """Regression for bug 12: low-balance players should still pay birthday fee."""
        g = Game(["Alice", "Bob", "Cara"])
        alice = g.players[0]
        bob = g.players[1]
        cara = g.players[2]

        bob.balance = 10
        cara.balance = 100

        card = {"description": "Birthday", "action": "birthday", "value": 50}
        g._apply_card(alice, card)

        assert bob.balance == -40
        assert cara.balance == 50
        assert alice.balance == STARTING_BALANCE + 100

    def test_birthday_card_triggers_immediate_bankruptcy_cleanup(self):
        """Regression for bug 16: players bankrupted by card effects should be removed immediately."""
        g = Game(["Alice", "Bob", "Cara"])
        alice = g.players[0]
        bob = g.players[1]
        cara = g.players[2]

        bob.balance = 10
        cara.balance = 100

        card = {"description": "Birthday", "action": "birthday", "value": 50}
        g._apply_card(alice, card)

        assert bob not in g.players


class TestGameMoveAndResolve:
    """Test tile resolution after movement."""

    @patch("moneypoly.game.ui.confirm", return_value=False)
    @patch("builtins.input", return_value="s")  # skip buying
    def test_landing_on_income_tax(self, _input, _confirm):
        g = Game(["Alice", "Bob"])
        player = g.current_player()
        initial = player.balance
        g._move_and_resolve(player, 4)  # income tax position
        assert player.balance == initial - INCOME_TAX_AMOUNT

    @patch("moneypoly.game.ui.confirm", return_value=False)
    @patch("builtins.input", return_value="s")
    def test_landing_on_go_to_jail(self, _input, _confirm):
        g = Game(["Alice", "Bob"])
        player = g.current_player()
        player.position = 25
        g._move_and_resolve(player, 5)  # go to jail at 30
        assert player.jail_info["in_jail"]


class TestGameJailAndTurnRegression:
    """Regression tests for jail fine handling and turn index behavior."""

    @patch("moneypoly.game.ui.confirm", return_value=True)
    @patch("moneypoly.game.Dice.roll", return_value=0)
    @patch("moneypoly.game.Game._move_and_resolve")
    def test_voluntary_jail_fine_deducts_from_player(
        self,
        _move_and_resolve,
        _roll,
        _confirm,
    ):
        """Regression for bug 14: paying to leave jail must reduce player balance."""
        g = Game(["Alice", "Bob"])
        player = g.players[0]
        player.go_to_jail()
        initial_player = player.balance
        initial_bank = g.bank.get_balance()

        g._handle_jail_turn(player)

        assert player.balance == initial_player - JAIL_FINE
        assert g.bank.get_balance() == initial_bank + JAIL_FINE
        assert not player.jail_info["in_jail"]

    def test_bankruptcy_during_turn_does_not_skip_next_player(self):
        """Regression for bug 15: removing current player should not skip next player."""
        g = Game(["P1", "P2", "P3", "P4"])
        g.state["current_index"] = 1
        eliminated = g.players[1]
        eliminated.balance = 0

        g._check_bankruptcy(eliminated)
        g.advance_turn()

        assert g.current_player().name == "P3"
