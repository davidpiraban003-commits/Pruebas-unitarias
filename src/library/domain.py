"""Capa de dominio: entidades, reglas puras y excepciones.

No depende de ningún framework ni de la base de datos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

LOAN_DAYS = 14
MAX_ACTIVE_LOANS = 3
FINE_PER_DAY = 500  # COP por día de retraso

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ISBN_RE = re.compile(r"^(\d{13}|\d{9}[\dX])$")


class LibraryError(Exception):
    """Error base del dominio."""


class ValidationError(LibraryError):
    """Datos de entrada inválidos."""


class NotFoundError(LibraryError):
    """Recurso inexistente."""


class ConflictError(LibraryError):
    """El recurso ya existe."""


class BusinessRuleError(LibraryError):
    """Se violó una regla de negocio."""


def normalize_isbn(raw: str) -> str:
    """Quita guiones/espacios y valida formato ISBN-10 o ISBN-13."""
    if not isinstance(raw, str):
        raise ValidationError("El ISBN debe ser texto.")
    isbn = raw.replace("-", "").replace(" ", "").upper()
    if not _ISBN_RE.match(isbn):
        raise ValidationError("ISBN inválido: debe tener 10 o 13 dígitos.")
    return isbn


def _clean_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} es obligatorio.")
    return value.strip()


@dataclass
class Book:
    isbn: str
    title: str
    author: str
    total_copies: int = 1
    available_copies: int | None = None

    def __post_init__(self) -> None:
        self.isbn = normalize_isbn(self.isbn)
        self.title = _clean_text(self.title, "El título")
        self.author = _clean_text(self.author, "El autor")
        if (
            not isinstance(self.total_copies, int)
            or isinstance(self.total_copies, bool)
            or self.total_copies < 1
        ):
            raise ValidationError("Las copias deben ser un entero >= 1.")
        if self.available_copies is None:
            self.available_copies = self.total_copies

    def checkout(self) -> None:
        if self.available_copies == 0:
            raise BusinessRuleError("No hay copias disponibles.")
        self.available_copies -= 1

    def restock(self) -> None:
        if self.available_copies >= self.total_copies:
            raise BusinessRuleError("Todas las copias ya están en la biblioteca.")
        self.available_copies += 1


@dataclass
class Member:
    name: str
    email: str
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = _clean_text(self.name, "El nombre")
        self.email = _clean_text(self.email, "El correo").lower()
        if not _EMAIL_RE.match(self.email):
            raise ValidationError("Correo electrónico inválido.")


@dataclass
class Loan:
    member_id: int
    isbn: str
    loaned_on: date
    due_on: date
    returned_on: date | None = None
    fine: int = 0
    id: int | None = None

    @classmethod
    def start(cls, member_id: int, isbn: str, today: date) -> Loan:
        return cls(member_id, isbn, today, today + timedelta(days=LOAN_DAYS))

    @property
    def is_active(self) -> bool:
        return self.returned_on is None

    def is_overdue(self, today: date) -> bool:
        return self.is_active and today > self.due_on

    def calculate_fine(self, on: date) -> int:
        return max(0, (on - self.due_on).days) * FINE_PER_DAY

    def close(self, today: date) -> int:
        if not self.is_active:
            raise BusinessRuleError("El préstamo ya fue devuelto.")
        if today < self.loaned_on:
            raise ValidationError("La devolución no puede ser anterior al préstamo.")
        self.returned_on = today
        self.fine = self.calculate_fine(today)
        return self.fine
