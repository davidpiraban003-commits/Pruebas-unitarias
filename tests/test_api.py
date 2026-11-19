import pytest
from fastapi.testclient import TestClient

from library.api import create_app

from .conftest import FakeClock

ISBN = "9780306406157"


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def client(clock):
    return TestClient(create_app(clock=clock))


def seed(client):
    client.post("/books", json={"isbn": ISBN, "title": "Clean Code", "author": "Martin", "copies": 1})
    client.post("/members", json={"name": "Ana", "email": "ana@x.com"})


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_search_book(client):
    r = client.post("/books", json={"isbn": ISBN, "title": "Clean Code", "author": "Martin"})
    assert r.status_code == 201
    assert client.get("/books", params={"q": "clean"}).json()[0]["isbn"] == ISBN
    assert client.get("/books").json()[0]["available_copies"] == 1


def test_duplicate_book_409(client):
    seed(client)
    r = client.post("/books", json={"isbn": ISBN, "title": "X", "author": "Y"})
    assert r.status_code == 409


def test_invalid_isbn_422(client):
    r = client.post("/books", json={"isbn": "1", "title": "X", "author": "Y"})
    assert r.status_code == 422


def test_missing_field_422(client):
    assert client.post("/members", json={"name": "Ana"}).status_code == 422


def test_full_loan_flow_with_fine(client, clock):
    seed(client)
    loan = client.post("/loans", json={"member_id": 1, "isbn": ISBN})
    assert loan.status_code == 201
    assert len(client.get("/members/1/loans").json()) == 1
    clock.advance(16)
    r = client.post(f"/loans/{loan.json()['id']}/return")
    assert r.status_code == 200 and r.json()["fine"] == 1000
    assert client.get("/members/1/loans").json() == []


def test_borrow_unavailable_book_422(client):
    seed(client)
    client.post("/members", json={"name": "Beto", "email": "b@x.com"})
    client.post("/loans", json={"member_id": 1, "isbn": ISBN})
    r = client.post("/loans", json={"member_id": 2, "isbn": ISBN})
    assert r.status_code == 422 and "copias" in r.json()["detail"]


@pytest.mark.parametrize("method,url,body", [
    ("post", "/loans", {"member_id": 9, "isbn": ISBN}),
    ("post", "/loans/9/return", None),
    ("get", "/members/9/loans", None),
])
def test_not_found_404(client, method, url, body):
    seed(client)
    r = getattr(client, method)(url, **({"json": body} if body else {}))
    assert r.status_code == 404
