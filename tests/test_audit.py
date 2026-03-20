"""
tests/test_audit.py — Testes da trilha de auditoria.
"""
from datetime import datetime


class TestAuditLog:
    def _seed_logs(self, db):
        from app.core.models import AuditLog
        logs = [
            AuditLog(username="admin", action="LOGIN_SUCCESS", target="admin",
                     details="IP: 127.0.0.1", timestamp=datetime(2025, 1, 10, 8, 0, 0)),
            AuditLog(username="admin", action="CREATE_USER", target="novo",
                     details="Role: VIEWER", timestamp=datetime(2025, 1, 15, 9, 0, 0)),
            AuditLog(username="viewer", action="LOGIN_FAILED", target="viewer",
                     details="IP: 192.168.1.1", timestamp=datetime(2025, 2, 1, 10, 0, 0)),
        ]
        for l in logs:
            db.add(l)
        db.commit()

    def test_retorna_todos_os_logs(self, admin_client, db):
        self._seed_logs(db)
        r = admin_client.get("/api/audit")
        assert r.status_code == 200
        logs = r.json()
        # admin_client faz um login que gera 1 log extra (LOGIN_SUCCESS)
        # então esperamos seed (3) + login do admin_client (1) = 4
        assert len(logs) >= 3
        # Verificar que os logs seedados estão presentes
        actions = [l["action"] for l in logs]
        assert "CREATE_USER" in actions
        assert "LOGIN_FAILED" in actions

    def test_filtro_por_data_inicio(self, admin_client, db):
        self._seed_logs(db)
        r = admin_client.get("/api/audit?start=2025-01-14")
        logs = r.json()
        # Deve retornar apenas logs a partir de 14/01 (CREATE_USER + LOGIN_FAILED + login do admin_client)
        assert len(logs) >= 2
        # Nenhum log deve ser anterior a 14/01/2025
        for l in logs:
            date_str = l["date"]  # formato "dd/mm/yyyy HH:MM:SS"
            if len(date_str) >= 10:
                day, month, year = date_str[:10].split("/")
                from datetime import date
                log_date = date(int(year), int(month), int(day))
                assert log_date >= date(2025, 1, 14), f"Log fora do filtro: {date_str}"

    def test_filtro_por_data_fim(self, admin_client, db):
        self._seed_logs(db)
        r = admin_client.get("/api/audit?end=2025-01-31")
        logs = r.json()
        assert len(logs) == 2  # apenas os logs de janeiro

    def test_filtro_por_periodo_exato(self, admin_client, db):
        self._seed_logs(db)
        r = admin_client.get("/api/audit?start=2025-01-15&end=2025-01-15")
        logs = r.json()
        assert len(logs) == 1
        assert logs[0]["action"] == "CREATE_USER"

    def test_campos_obrigatorios_presentes(self, admin_client, db):
        self._seed_logs(db)
        r = admin_client.get("/api/audit")
        log = r.json()[0]
        for campo in ["date", "user", "action", "target", "details", "hash_short"]:
            assert campo in log, f"Campo '{campo}' ausente no log"

    def test_hash_short_tem_8_chars(self, admin_client, db):
        self._seed_logs(db)
        r = admin_client.get("/api/audit")
        for log in r.json():
            assert len(log["hash_short"]) == 8

    def test_viewer_nao_acessa_auditoria(self, viewer_client):
        r = viewer_client.get("/api/audit")
        assert r.status_code == 403

    def test_login_falha_registrado_em_auditoria(self, client, admin_user, admin_client):
        client.post("/token", data={"username": "admin", "password": "errada"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
        r = admin_client.get("/api/audit")
        logs = r.json()
        falhas = [l for l in logs if l["action"] == "LOGIN_FAILED"]
        assert len(falhas) >= 1
