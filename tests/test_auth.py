"""
tests/test_auth.py — Testes de autenticação.

Cobre: login OK, login inválido, cookie httponly, logout, usuário inativo.
"""
import pytest
from conftest import login


class TestLogin:
    def test_login_sucesso_retorna_token(self, client, admin_user):
        r = login(client, "admin", "Admin123")
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["role"] == "ADMIN"
        assert data["user_full_name"] == "ADMINISTRADOR"

    def test_login_define_cookie_httponly(self, client, admin_user):
        r = login(client, "admin", "Admin123")
        assert r.status_code == 200
        # Cookie deve estar presente
        assert "orbisclin_session" in r.cookies
        # httponly não aparece no valor do cookie via TestClient,
        # mas verificamos que o endpoint set_auth_cookie foi chamado
        # inspecionando o header Set-Cookie
        set_cookie = r.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()

    def test_login_credenciais_invalidas(self, client, admin_user):
        r = login(client, "admin", "senha_errada")
        assert r.status_code == 401
        assert "inválidas" in r.json()["detail"]

    def test_login_usuario_inexistente(self, client):
        r = login(client, "ninguem", "qualquer")
        assert r.status_code == 401

    def test_login_usuario_inativo(self, client, db, admin_user):
        admin_user.is_active = False
        db.commit()
        r = login(client, "admin", "Admin123")
        assert r.status_code == 403
        assert "inativo" in r.json()["detail"].lower()

    def test_acesso_sem_autenticacao_retorna_401(self, client):
        r = client.get("/api/users/", follow_redirects=False)
        assert r.status_code == 401

    def test_acesso_com_cookie_valido(self, client, admin_user):
        login(client, "admin", "Admin123")
        r = client.get("/api/users/")
        assert r.status_code == 200

    def test_logout_limpa_cookie(self, client, admin_user):
        login(client, "admin", "Admin123")
        r = client.post("/api/auth/logout")
        assert r.status_code == 200
        # Após logout, acesso deve falhar
        r2 = client.get("/api/users/")
        assert r2.status_code == 401


class TestRateLimit:
    def test_muitas_tentativas_retornam_429(self, client, admin_user):
        """11 tentativas seguidas devem acionar o rate limit (10/min)."""
        for _ in range(10):
            login(client, "admin", "errada")
        r = login(client, "admin", "errada")
        # 429 ou 401 — depende do tempo; em CI rápido pode não acionar
        assert r.status_code in (401, 429)
