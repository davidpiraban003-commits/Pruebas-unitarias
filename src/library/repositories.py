"""Repositorios (puertos) e implementaciones en memoria."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .domain import Book, ConflictError, Loan, Member


class BookRepository(ABC):
    @abstractmethod
    def add(self, book: Book) -> None: ...
    @abstractmethod
    def get(self, isbn: str) -> Book | None: ...
    @abstractmethod
    def save(self, book: Book) -> None: ...
    @abstractmethod
    def search(self, query: str) -> list[Book]: ...


class MemberRepository(ABC):
    @abstractmethod
    def add(self, member: Member) -> Member: ...
    @abstractmethod
    def get(self, member_id: int) -> Member | None: ...


class LoanRepository(ABC):
    @abstractmethod
    def add(self, loan: Loan) -> Loan: ...
    @abstractmethod
    def get(self, loan_id: int) -> Loan | None: ...
    @abstractmethod
    def active_by_member(self, member_id: int) -> list[Loan]: ...


class InMemoryBookRepository(BookRepository):
    def __init__(self) -> None:
        self._data: dict[str, Book] = {}

    def add(self, book: Book) -> None:
        if book.isbn in self._data:
            raise ConflictError("Ya existe un libro con ese ISBN.")
        self._data[book.isbn] = book

    def get(self, isbn: str) -> Book | None:
        return self._data.get(isbn)

    def save(self, book: Book) -> None:
        self._data[book.isbn] = book

    def search(self, query: str) -> list[Book]:
        q = query.strip().lower()
        return [
            b for b in self._data.values()
            if q in b.title.lower() or q in b.author.lower()
        ]


class InMemoryMemberRepository(MemberRepository):
    def __init__(self) -> None:
        self._data: dict[int, Member] = {}
        self._next_id = 1

    def add(self, member: Member) -> Member:
        if any(m.email == member.email for m in self._data.values()):
            raise ConflictError("Ya existe un socio con ese correo.")
        member.id = self._next_id
        self._data[member.id] = member
        self._next_id += 1
        return member

    def get(self, member_id: int) -> Member | None:
        return self._data.get(member_id)


class InMemoryLoanRepository(LoanRepository):
    def __init__(self) -> None:
        self._data: dict[int, Loan] = {}
        self._next_id = 1

    def add(self, loan: Loan) -> Loan:
        loan.id = self._next_id
        self._data[loan.id] = loan
        self._next_id += 1
        return loan

    def get(self, loan_id: int) -> Loan | None:
        return self._data.get(loan_id)

    def active_by_member(self, member_id: int) -> list[Loan]:
        return [
            l for l in self._data.values()
            if l.member_id == member_id and l.is_active
        ]
