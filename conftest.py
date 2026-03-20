"""
tests/conftest.py — Fixtures compartilhadas entre todos os testes.

Usa banco SQLite em memória para isolamento total.
Cada teste recebe um banco limpo via fixture de session.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Banco em memória — isolado por test session
TEST_DB_URL = "sqlite:///./test_orbisclin.db"

# Precisa ser configurado ANTES de importar main/database
import os
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["SECRET_KEY"] = "test_secret_key_for_pytest_only"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["STORAGE_DIR"] = "./test_storage"

from database import Base, get_db
from main import app
from models import User
from security import get_password_hash

engine_test = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function", autouse=True)
def fresh_db():
    """Cria todas as tabelas antes de cada teste e dropa depois."""
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    # Limpa arquivo de teste
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
    """Cliente de teste com banco isolado."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def db():
    """Sessão de banco para uso direto nos testes."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin_user(db):
    """Cria e retorna um usuário ADMIN no banco de teste."""
    u = User(
        username="admin",
        hashed_password=get_password_hash("Admin123"),
        full_name="ADMINISTRADOR",
        role="ADMIN",
        matricula="0001",
        birth_date="1990-01-01",
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def viewer_user(db):
    """Cria e retorna um usuário VIEWER no banco de teste."""
    u = User(
        username="viewer",
        hashed_password=get_password_hash("Viewer123"),
        full_name="VISUALIZADOR",
        role="VIEWER",
        matricula="0002",
        birth_date="1995-05-15",
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def login(client, username: str, password: str) -> dict:
    """Helper: faz login e retorna o response. Cookie é setado automaticamente."""
    r = client.post(
        "/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return r


@pytest.fixture
def admin_client(client, admin_user):
    """Cliente já autenticado como ADMIN (cookie setado)."""
    login(client, "admin", "Admin123")
    return client


@pytest.fixture
def viewer_client(client, viewer_user):
    """Cliente já autenticado como VIEWER (cookie setado)."""
    login(client, "viewer", "Viewer123")
    return client
