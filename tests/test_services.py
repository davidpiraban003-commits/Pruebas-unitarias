import pytest

from library.domain import (
    FINE_PER_DAY,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


class TestCatalogAndMembers:
    def test_duplicate_isbn_conflict(self, service, book):
        with pytest.raises(ConflictError):
            service.add_book("9780306406157", "Otro", "X")

    def test_invalid_book_not_stored(self, service):
        with pytest.raises(ValidationError):
            service.add_book("bad", "T", "A")
        assert service.search_books("") == []

    def test_search_by_title_and_author_case_insensitive(self, service, book):
        assert service.search_books("clean")[0].isbn == book.isbn
        assert service.search_books("MARTIN")[0].isbn == book.isbn
        assert service.search_books("zzz") == []

    def test_duplicate_email_conflict(self, service, member):
        with pytest.raises(ConflictError):
            service.register_member("Otra", "ANA@correo.com")

    def test_member_gets_incremental_ids(self, service):
        a = service.register_member("A", "a@a.com")
        b = service.register_member("B", "b@b.com")
        assert (a.id, b.id) == (1, 2)


class TestBorrow:
    def test_happy_path(self, service, member, book, clock):
        loan = service.borrow_book(member.id, book.isbn)
        assert loan.id == 1
        assert loan.due_on == clock.today.replace(day=24)
        assert book.available_copies == 1

    def test_accepts_formatted_isbn(self, service, member, book):
        assert service.borrow_book(member.id, "978-0-306-40615-7").isbn == book.isbn

    def test_unknown_member(self, service, book):
        with pytest.raises(NotFoundError):
            service.borrow_book(99, book.isbn)

    def test_unknown_book(self, service, member):
        with pytest.raises(NotFoundError):
            service.borrow_book(member.id, "9780000000002")

    def test_invalid_isbn(self, service, member):
        with pytest.raises(ValidationError):
            service.borrow_book(member.id, "xx")

    def test_no_copies_left(self, service, book):
        for i in range(2):
            m = service.register_member(f"M{i}", f"m{i}@x.com")
            service.borrow_book(m.id, book.isbn)
        late = service.register_member("Late", "late@x.com")
        with pytest.raises(BusinessRuleError):
            service.borrow_book(late.id, book.isbn)
        assert book.available_copies == 0

    def test_same_book_twice_rejected_and_stock_intact(self, service, member, book):
        service.borrow_book(member.id, book.isbn)
        with pytest.raises(BusinessRuleError):
            service.borrow_book(member.id, book.isbn)
        assert book.available_copies == 1

    def test_max_three_active_loans(self, service, member):
        for i in range(3):
            b = service.add_book(f"97800000000{i:02d}"[:13].ljust(13, "0"), f"L{i}", "A")
            service.borrow_book(member.id, b.isbn)
        extra = service.add_book("9781111111111", "Extra", "A")
        with pytest.raises(BusinessRuleError, match="Máximo"):
            service.borrow_book(member.id, extra.isbn)
        assert extra.available_copies == 1

    def test_overdue_loan_blocks_new_borrow(self, service, member, book, clock):
        service.borrow_book(member.id, book.isbn)
        other = service.add_book("9782222222222", "Otro", "A")
        clock.advance(14)  # justo en la fecha límite: aún permitido
        service.borrow_book(member.id, other.isbn)
        third = service.add_book("9783333333333", "Tercero", "A")
        clock.advance(1)  # ahora vencido
        with pytest.raises(BusinessRuleError, match="vencidos"):
            service.borrow_book(member.id, third.isbn)


class TestReturn:
    def test_on_time_no_fine_and_restock(self, service, member, book, clock):
        loan = service.borrow_book(member.id, book.isbn)
        clock.advance(14)
        returned = service.return_book(loan.id)
        assert returned.fine == 0
        assert book.available_copies == 2

    def test_late_fine(self, service, member, book, clock):
        loan = service.borrow_book(member.id, book.isbn)
        clock.advance(17)
        assert service.return_book(loan.id).fine == 3 * FINE_PER_DAY

    def test_unknown_loan(self, service):
        with pytest.raises(NotFoundError):
            service.return_book(42)

    def test_double_return_does_not_duplicate_stock(self, service, member, book):
        loan = service.borrow_book(member.id, book.isbn)
        service.return_book(loan.id)
        with pytest.raises(BusinessRuleError):
            service.return_book(loan.id)
        assert book.available_copies == 2

    def test_can_borrow_again_after_return(self, service, member, book):
        loan = service.borrow_book(member.id, book.isbn)
        service.return_book(loan.id)
        assert service.borrow_book(member.id, book.isbn).id == 2


class TestActiveLoans:
    def test_lists_only_active(self, service, member, book):
        loan = service.borrow_book(member.id, book.isbn)
        assert [l.id for l in service.active_loans_of(member.id)] == [loan.id]
        service.return_book(loan.id)
        assert service.active_loans_of(member.id) == []

    def test_unknown_member(self, service):
        with pytest.raises(NotFoundError):
            service.active_loans_of(7)
