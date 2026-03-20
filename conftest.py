"""
conftest.py — Fixtures de teste. Localização: raiz do projeto.
"""
import os
import pytest

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"]   = "test_secret_key_for_pytest_only"
os.environ["REDIS_URL"]    = "redis://localhost:6379/0"
os.environ["STORAGE_DIR"]  = "/tmp/test_storage_orbisclin"
os.environ["TESTING"]      = "1"   # flag para desabilitar rate limit

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pathlib

engine_test = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

from app.core.database import Base, get_db
from app.core.models import User
from app.core.security import get_password_hash

import app.core.database as _db_module
_db_module.engine       = engine_test
_db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
_db_module.STORAGE_DIR  = pathlib.Path("/tmp/test_storage_orbisclin")
_db_module.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

import main as _main_module
_main_module._create_default_admin = lambda: None

# Desabilita rate limiting: substitui o limiter.limit por um passthrough
from slowapi import Limiter
from slowapi.util import get_remote_address
_noop_limiter = Limiter(key_func=get_remote_address, enabled=False)
# Monkey-patch no módulo auth antes do import do app
import app.routers.auth as _auth_module
_auth_module.limiter = _noop_limiter

from main import app
from fastapi.testclient import TestClient

# Substitui o limiter do app também
app.state.limiter = _noop_limiter

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def fresh_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


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
    u = User(
        username="admin", hashed_password=get_password_hash("Admin123"),
        full_name="ADMINISTRADOR", role="ADMIN",
        matricula="0001", birth_date="1990-01-01", is_active=True,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture
def viewer_user(db):
    u = User(
        username="viewer", hashed_password=get_password_hash("Viewer123"),
        full_name="VISUALIZADOR", role="VIEWER",
        matricula="0002", birth_date="1995-05-15", is_active=True,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def login(client, username: str, password: str):
    return client.post(
        "/token",
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
