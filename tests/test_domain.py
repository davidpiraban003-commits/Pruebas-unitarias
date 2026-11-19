from datetime import date

import pytest

from library.domain import (
    FINE_PER_DAY,
    Book,
    BusinessRuleError,
    Loan,
    Member,
    ValidationError,
    normalize_isbn,
)


class TestIsbn:
    @pytest.mark.parametrize("raw,expected", [
        ("978-0-306-40615-7", "9780306406157"),
        ("0-306-40615-2", "0306406152"),
        ("080442957x", "080442957X"),
        (" 9780306406157 ", "9780306406157"),
    ])
    def test_valid(self, raw, expected):
        assert normalize_isbn(raw) == expected

    @pytest.mark.parametrize("raw", ["", "123", "abcdefghij", "97803064061577", None, 123])
    def test_invalid(self, raw):
        with pytest.raises(ValidationError):
            normalize_isbn(raw)


class TestBook:
    def test_defaults_available_to_total(self):
        b = Book("9780306406157", "T", "A", 3)
        assert b.available_copies == 3

    @pytest.mark.parametrize("copies", [0, -1, True, 1.5, "2"])
    def test_invalid_copies(self, copies):
        with pytest.raises(ValidationError):
            Book("9780306406157", "T", "A", copies)

    @pytest.mark.parametrize("title,author", [("", "A"), ("  ", "A"), ("T", ""), ("T", None)])
    def test_invalid_text(self, title, author):
        with pytest.raises(ValidationError):
            Book("9780306406157", title, author)

    def test_checkout_until_empty(self):
        b = Book("9780306406157", "T", "A", 1)
        b.checkout()
        assert b.available_copies == 0
        with pytest.raises(BusinessRuleError):
            b.checkout()

    def test_restock_cannot_exceed_total(self):
        b = Book("9780306406157", "T", "A", 1)
        with pytest.raises(BusinessRuleError):
            b.restock()

    def test_trims_text(self):
        b = Book("9780306406157", "  T  ", " A ")
        assert (b.title, b.author) == ("T", "A")


class TestMember:
    def test_email_normalized(self):
        assert Member("Ana", "ANA@Correo.COM").email == "ana@correo.com"

    @pytest.mark.parametrize("email", ["sin-arroba", "a@b", "a @b.com", "@b.com", ""])
    def test_invalid_email(self, email):
        with pytest.raises(ValidationError):
            Member("Ana", email)

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            Member("  ", "a@b.com")


class TestLoan:
    def test_due_date_is_14_days(self):
        loan = Loan.start(1, "9780306406157", date(2026, 1, 1))
        assert loan.due_on == date(2026, 1, 15)

    @pytest.mark.parametrize("day,overdue", [(15, False), (16, True)])
    def test_overdue_boundary(self, day, overdue):
        loan = Loan.start(1, "x", date(2026, 1, 1))
        assert loan.is_overdue(date(2026, 1, day)) is overdue

    @pytest.mark.parametrize("day,fine", [(10, 0), (15, 0), (16, FINE_PER_DAY), (20, 5 * FINE_PER_DAY)])
    def test_fine(self, day, fine):
        loan = Loan.start(1, "x", date(2026, 1, 1))
        assert loan.close(date(2026, 1, day)) == fine
        assert loan.fine == fine and not loan.is_active

    def test_close_twice_fails(self):
        loan = Loan.start(1, "x", date(2026, 1, 1))
        loan.close(date(2026, 1, 2))
        with pytest.raises(BusinessRuleError):
            loan.close(date(2026, 1, 3))

    def test_returned_loan_not_overdue(self):
        loan = Loan.start(1, "x", date(2026, 1, 1))
        loan.close(date(2026, 1, 2))
        assert loan.is_overdue(date(2026, 3, 1)) is False

    def test_close_before_loan_date_fails(self):
        loan = Loan.start(1, "x", date(2026, 1, 10))
        with pytest.raises(ValidationError):
            loan.close(date(2026, 1, 9))
