from datetime import date, timedelta

import pytest

from library.repositories import (
    InMemoryBookRepository,
    InMemoryLoanRepository,
    InMemoryMemberRepository,
)
from library.services import LibraryService


class FakeClock:
    """Reloj controlable para pruebas deterministas."""

    def __init__(self, today: date = date(2026, 1, 10)):
        self.today = today

    def __call__(self) -> date:
        return self.today

    def advance(self, days: int) -> None:
        self.today += timedelta(days=days)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def service(clock):
    return LibraryService(
        InMemoryBookRepository(),
        InMemoryMemberRepository(),
        InMemoryLoanRepository(),
        clock,
    )


@pytest.fixture
def member(service):
    return service.register_member("Ana Pérez", "ana@correo.com")


@pytest.fixture
def book(service):
    return service.add_book("978-0-306-40615-7", "Clean Code", "Robert Martin", 2)
