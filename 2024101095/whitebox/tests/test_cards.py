"""White-box tests for the CardDeck module."""
from moneypoly.cards import CardDeck, CHANCE_CARDS, COMMUNITY_CHEST_CARDS


class TestCardDeckInit:
    """Test deck initialization."""

    def test_creates_deck(self):
        deck = CardDeck(CHANCE_CARDS)
        assert len(deck) == len(CHANCE_CARDS)
        assert deck.index == 0

    def test_empty_deck(self):
        deck = CardDeck([])
        assert len(deck) == 0


class TestCardDeckDraw:
    """Test drawing cards."""

    def test_draw_returns_card(self):
        deck = CardDeck(CHANCE_CARDS)
        card = deck.draw()
        assert card is not None
        assert "description" in card

    def test_draw_advances_index(self):
        deck = CardDeck(CHANCE_CARDS)
        deck.draw()
        assert deck.index == 1

    def test_draw_cycles(self):
        cards = [{"description": "A"}, {"description": "B"}]
        deck = CardDeck(cards)
        deck.draw()
        deck.draw()
        card = deck.draw()
        assert card["description"] == "A"

    def test_draw_empty_returns_none(self):
        deck = CardDeck([])
        assert deck.draw() is None


class TestCardDeckPeek:
    """Test peeking at next card."""

    def test_peek_returns_next(self):
        deck = CardDeck(CHANCE_CARDS)
        card = deck.peek()
        assert card == CHANCE_CARDS[0]

    def test_peek_does_not_advance(self):
        deck = CardDeck(CHANCE_CARDS)
        deck.peek()
        assert deck.index == 0

    def test_peek_empty_returns_none(self):
        deck = CardDeck([])
        assert deck.peek() is None


class TestCardDeckReshuffle:
    """Test reshuffling."""

    def test_reshuffle_resets_index(self):
        deck = CardDeck(CHANCE_CARDS)
        deck.draw()
        deck.draw()
        deck.reshuffle()
        assert deck.index == 0


class TestCardDeckMisc:
    """Test miscellaneous methods."""

    def test_cards_remaining(self):
        deck = CardDeck(CHANCE_CARDS)
        remaining = deck.cards_remaining()
        assert remaining == len(CHANCE_CARDS)
        deck.draw()
        assert deck.cards_remaining() == len(CHANCE_CARDS) - 1

    def test_repr(self):
        deck = CardDeck(CHANCE_CARDS)
        assert "CardDeck" in repr(deck)

    def test_empty_deck_cards_remaining_is_safe(self):
        deck = CardDeck([])
        assert deck.cards_remaining() == 0

    def test_empty_deck_repr_is_safe(self):
        deck = CardDeck([])
        assert repr(deck) == "CardDeck(0 cards)"


class TestCardData:
    """Test card data validity."""

    def test_chance_cards_have_required_fields(self):
        for card in CHANCE_CARDS:
            assert "description" in card
            assert "action" in card
            assert "value" in card

    def test_community_chest_cards_have_required_fields(self):
        for card in COMMUNITY_CHEST_CARDS:
            assert "description" in card
            assert "action" in card
            assert "value" in card

    def test_valid_actions(self):
        valid = {"collect", "pay", "jail", "jail_free", "move_to",
                 "birthday", "collect_from_all"}
        for card in CHANCE_CARDS + COMMUNITY_CHEST_CARDS:
            assert card["action"] in valid
