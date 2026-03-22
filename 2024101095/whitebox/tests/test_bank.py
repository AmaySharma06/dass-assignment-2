"""White-box tests for the Bank module."""
import pytest
from moneypoly.bank import Bank
from moneypoly.player import Player
from moneypoly.config import BANK_STARTING_FUNDS


class TestBankInit:
    """Test bank initialization."""

    def test_initial_balance(self):
        b = Bank()
        assert b.get_balance() == BANK_STARTING_FUNDS

    def test_initial_loans(self):
        b = Bank()
        assert b.loan_count() == 0
        assert b.total_loans_issued() == 0


class TestBankCollect:
    """Test collecting funds."""

    def test_collect_positive(self):
        b = Bank()
        b.collect(100)
        assert b.get_balance() == BANK_STARTING_FUNDS + 100

    def test_collect_zero(self):
        b = Bank()
        b.collect(0)
        assert b.get_balance() == BANK_STARTING_FUNDS

    def test_collect_negative_is_ignored(self):
        """Regression for bug 5: negative collect must not drain bank funds."""
        b = Bank()
        b.collect(-100)
        assert b.get_balance() == BANK_STARTING_FUNDS


class TestBankPayOut:
    """Test paying out funds."""

    def test_pay_out_valid(self):
        b = Bank()
        amount = b.pay_out(100)
        assert amount == 100
        assert b.get_balance() == BANK_STARTING_FUNDS - 100

    def test_pay_out_zero(self):
        b = Bank()
        assert b.pay_out(0) == 0
        assert b.get_balance() == BANK_STARTING_FUNDS

    def test_pay_out_negative(self):
        b = Bank()
        assert b.pay_out(-10) == 0

    def test_pay_out_exceeds_balance(self):
        b = Bank()
        with pytest.raises(ValueError):
            b.pay_out(BANK_STARTING_FUNDS + 1)

    def test_pay_out_exactly_balance(self):
        b = Bank()
        amount = b.pay_out(BANK_STARTING_FUNDS)
        assert amount == BANK_STARTING_FUNDS
        assert b.get_balance() == 0


class TestBankLoans:
    """Test loan issuance."""

    def test_give_loan(self):
        b = Bank()
        p = Player("Alice", balance=100)
        initial_bank = b.get_balance()
        b.give_loan(p, 200)
        assert p.balance == 300
        assert b.get_balance() == initial_bank - 200
        assert b.loan_count() == 1
        assert b.total_loans_issued() == 200

    def test_give_loan_zero(self):
        b = Bank()
        p = Player("Alice", balance=100)
        b.give_loan(p, 0)
        assert p.balance == 100
        assert b.loan_count() == 0

    def test_give_loan_negative(self):
        b = Bank()
        p = Player("Alice", balance=100)
        b.give_loan(p, -50)
        assert p.balance == 100

    def test_multiple_loans(self):
        b = Bank()
        p1 = Player("Alice", balance=100)
        p2 = Player("Bob", balance=100)
        b.give_loan(p1, 200)
        b.give_loan(p2, 300)
        assert b.loan_count() == 2
        assert b.total_loans_issued() == 500


class TestBankDisplay:
    """Test display methods."""

    def test_summary(self, capsys):
        b = Bank()
        b.summary()
        captured = capsys.readouterr()
        assert "Bank reserves" in captured.out

    def test_repr(self):
        b = Bank()
        assert "Bank" in repr(b)
