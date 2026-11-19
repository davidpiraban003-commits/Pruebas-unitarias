"""Capa de aplicación: casos de uso de la biblioteca."""
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from .domain import (
    MAX_ACTIVE_LOANS,
    Book,
    BusinessRuleError,
    Loan,
    Member,
    NotFoundError,
    normalize_isbn,
)
from .repositories import BookRepository, LoanRepository, MemberRepository


class LibraryService:
    def __init__(
        self,
        books: BookRepository,
        members: MemberRepository,
        loans: LoanRepository,
        clock: Callable[[], date] = date.today,
    ) -> None:
        self._books = books
        self._members = members
        self._loans = loans
        self._clock = clock

    # --- catálogo ---
    def add_book(self, isbn: str, title: str, author: str, copies: int = 1) -> Book:
        book = Book(isbn, title, author, copies)
        self._books.add(book)
        return book

    def search_books(self, query: str) -> list[Book]:
        return self._books.search(query)

    # --- socios ---
    def register_member(self, name: str, email: str) -> Member:
        return self._members.add(Member(name, email))

    # --- préstamos ---
    def borrow_book(self, member_id: int, isbn: str) -> Loan:
        today = self._clock()
        member = self._members.get(member_id)
        if member is None:
            raise NotFoundError("Socio no encontrado.")
        book = self._books.get(normalize_isbn(isbn))
        if book is None:
            raise NotFoundError("Libro no encontrado.")

        active = self._loans.active_by_member(member_id)
        if any(l.is_overdue(today) for l in active):
            raise BusinessRuleError("El socio tiene préstamos vencidos.")
        if len(active) >= MAX_ACTIVE_LOANS:
            raise BusinessRuleError(
                f"Máximo {MAX_ACTIVE_LOANS} préstamos activos por socio."
            )
        if any(l.isbn == book.isbn for l in active):
            raise BusinessRuleError("El socio ya tiene prestado este libro.")

        book.checkout()  # puede fallar si no hay copias; nada se persistió aún
        self._books.save(book)
        return self._loans.add(Loan.start(member_id, book.isbn, today))

    def return_book(self, loan_id: int) -> Loan:
        loan = self._loans.get(loan_id)
        if loan is None:
            raise NotFoundError("Préstamo no encontrado.")
        book = self._books.get(loan.isbn)
        loan.close(self._clock())
        book.restock()
        self._books.save(book)
        return loan

    def active_loans_of(self, member_id: int) -> list[Loan]:
        if self._members.get(member_id) is None:
            raise NotFoundError("Socio no encontrado.")
        return self._loans.active_by_member(member_id)
