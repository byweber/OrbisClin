"""
tests/conftest.py — Fixtures compartilhadas entre todos os testes.
Localização: tests/ na raiz do projeto.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_URL  = "sqlite:///./test_orbisclin.db"

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["SECRET_KEY"]   = "test_secret_key_for_pytest_only"
os.environ["REDIS_URL"]    = "redis://localhost:6379/0"
os.environ["STORAGE_DIR"]  = "./test_storage"

from app.core.database import Base, get_db
from app.core.models import User
from app.core.security import get_password_hash
from main import app

engine_test          = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal  = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function", autouse=True)
def fresh_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    if os.path.exists("./test_orbisclin.db"):
        os.remove("./test_orbisclin.db")


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin_user(db):
    u = User(username="admin", hashed_password=get_password_hash("Admin123"),
             full_name="ADMINISTRADOR", role="ADMIN", matricula="0001",
             birth_date="1990-01-01", is_active=True)
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture
def viewer_user(db):
    u = User(username="viewer", hashed_password=get_password_hash("Viewer123"),
             full_name="VISUALIZADOR", role="VIEWER", matricula="0002",
             birth_date="1995-05-15", is_active=True)
    db.add(u); db.commit(); db.refresh(u)
    return u


def login(client, username: str, password: str):
    return client.post("/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


@pytest.fixture
def admin_client(client, admin_user):
    login(client, "admin", "Admin123")
    return client


@pytest.fixture
def viewer_client(client, viewer_user):
    login(client, "viewer", "Viewer123")
    return client
