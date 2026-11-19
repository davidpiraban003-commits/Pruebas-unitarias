"""Capa de presentación: API REST con FastAPI."""
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .domain import (
    BusinessRuleError,
    ConflictError,
    LibraryError,
    NotFoundError,
    ValidationError,
)
from .repositories import (
    InMemoryBookRepository,
    InMemoryLoanRepository,
    InMemoryMemberRepository,
)
from .services import LibraryService

_STATUS = {
    ValidationError: 422,
    BusinessRuleError: 422,
    NotFoundError: 404,
    ConflictError: 409,
}


class BookIn(BaseModel):
    isbn: str
    title: str
    author: str
    copies: int = Field(default=1)


class MemberIn(BaseModel):
    name: str
    email: str


class BorrowIn(BaseModel):
    member_id: int
    isbn: str


def _loan_dict(loan) -> dict:
    return {
        "id": loan.id,
        "member_id": loan.member_id,
        "isbn": loan.isbn,
        "loaned_on": loan.loaned_on.isoformat(),
        "due_on": loan.due_on.isoformat(),
        "returned_on": loan.returned_on.isoformat() if loan.returned_on else None,
        "fine": loan.fine,
    }


def create_app(
    service: LibraryService | None = None,
    clock: Callable[[], date] = date.today,
) -> FastAPI:
    service = service or LibraryService(
        InMemoryBookRepository(),
        InMemoryMemberRepository(),
        InMemoryLoanRepository(),
        clock,
    )
    app = FastAPI(title="API Biblioteca", version="1.0.0")

    @app.exception_handler(LibraryError)
    async def handle_library_error(_: Request, exc: LibraryError):
        status = next((s for t, s in _STATUS.items() if isinstance(exc, t)), 400)
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/books", status_code=201)
    def add_book(body: BookIn):
        b = service.add_book(body.isbn, body.title, body.author, body.copies)
        return b.__dict__

    @app.get("/books")
    def search_books(q: str = ""):
        return [b.__dict__ for b in service.search_books(q)]

    @app.post("/members", status_code=201)
    def register_member(body: MemberIn):
        return service.register_member(body.name, body.email).__dict__

    @app.post("/loans", status_code=201)
    def borrow(body: BorrowIn):
        return _loan_dict(service.borrow_book(body.member_id, body.isbn))

    @app.post("/loans/{loan_id}/return")
    def return_book(loan_id: int):
        return _loan_dict(service.return_book(loan_id))

    @app.get("/members/{member_id}/loans")
    def member_loans(member_id: int):
        return [_loan_dict(l) for l in service.active_loans_of(member_id)]

    return app


app = create_app()
