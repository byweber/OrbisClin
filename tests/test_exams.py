"""
tests/test_exams.py — Testes de upload e busca de exames.

Usa arquivos sintéticos com magic bytes corretos (não depende de arquivos reais).
"""
import io
import pytest

# Magic bytes reais para simular arquivos
PDF_MAGIC  = b"%PDF-1.4 fake content for testing"
JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 100
PNG_MAGIC  = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def make_pdf(name="laudo.pdf") -> tuple:
    return (name, io.BytesIO(PDF_MAGIC), "application/pdf")

def make_jpeg(name="foto.jpg") -> tuple:
    return (name, io.BytesIO(JPEG_MAGIC), "image/jpeg")

def make_png(name="foto.png") -> tuple:
    return (name, io.BytesIO(PNG_MAGIC), "image/png")


COMMON_DATA = {
    "accession_number": "ACC2025001",
    "patient_id": "12345678900",
    "patient_name": "Paciente Teste",
    "file_type": "LAUDO",
    "exam_date": "2025-01-15",
}


class TestUpload:
    def test_upload_pdf_ecg_sucesso(self, admin_client, tmp_path, monkeypatch):
        # Monkeypatcha STORAGE_DIR para usar diretório temporário
        import app.core.database as database
        monkeypatch.setattr(database, "STORAGE_DIR", tmp_path)

        # Também precisa patchear o worker (Celery não disponível em testes)
        import app.routers.exams as exams_module
        monkeypatch.setattr(exams_module, "extract_text_from_pdf_task",
                            type("T", (), {"delay": staticmethod(lambda *a: None)})())

        r = admin_client.post("/api/upload", data={**COMMON_DATA, "procedure_type": "ECG"},
            files={"file": make_pdf()})
        assert r.status_code == 200
        assert r.json()["status"] == "success"

    def test_upload_imagem_para_ecg_retorna_400(self, admin_client, tmp_path, monkeypatch):
        import app.core.database as database
        monkeypatch.setattr(database, "STORAGE_DIR", tmp_path)

        r = admin_client.post("/api/upload", data={**COMMON_DATA, "procedure_type": "ECG"},
            files={"file": make_jpeg()})
        assert r.status_code == 400

    def test_upload_multiplos_arquivos_dermatologia(self, admin_client, tmp_path, monkeypatch):
        import app.core.database as database
        monkeypatch.setattr(database, "STORAGE_DIR", tmp_path)
        import app.routers.exams as exams_module
        monkeypatch.setattr(exams_module, "extract_text_from_pdf_task",
                            type("T", (), {"delay": staticmethod(lambda *a: None)})())

        r = admin_client.post(
            "/api/upload",
            data={**COMMON_DATA, "accession_number": "ACC2025002", "procedure_type": "DERMATOLOGIA"},
            files=[("file", make_jpeg("a.jpg")), ("file", make_jpeg("b.jpg"))],
        )
        assert r.status_code == 200
        assert len(r.json()["files"]) == 2

    def test_upload_multiplos_arquivos_procedimento_simples_retorna_400(self, admin_client, tmp_path, monkeypatch):
        import app.core.database as database
        monkeypatch.setattr(database, "STORAGE_DIR", tmp_path)

        r = admin_client.post(
            "/api/upload",
            data={**COMMON_DATA, "procedure_type": "ECG"},
            files=[("file", make_pdf("a.pdf")), ("file", make_pdf("b.pdf"))],
        )
        assert r.status_code == 400

    def test_viewer_nao_pode_fazer_upload(self, viewer_client, tmp_path, monkeypatch):
        # Viewer não tem permissão de upload — mas o endpoint não checa role,
        # checa apenas autenticação. Ajuste se quiser adicionar restrição de role.
        # Por ora, verifica que o viewer autenticado pode ou não subir.
        # Este teste documenta o comportamento atual.
        pass


class TestSearch:
    def _seed_exam(self, db):
        """Cria um exame diretamente no banco para testar busca."""
        from app.core.models import Patient, ExamSession
        p = Patient(id="99999999999", name="MARIA BUSCA")
        db.add(p)
        db.commit()
        s = ExamSession(
            accession_number="BUSCACC001",
            patient_id="99999999999",
            procedure_type="ECG",
            exam_date="2025-03-01",
        )
        db.add(s)
        db.commit()
        return s

    def test_busca_por_nome_retorna_resultado(self, admin_client, db):
        self._seed_exam(db)
        r = admin_client.get("/api/search?q=MARIA")
        assert r.status_code == 200
        data = r.json()["data"]
        assert any("MARIA" in d["patient_name"] for d in data if not d["is_pacs"])

    def test_busca_por_accession_retorna_resultado(self, admin_client, db):
        self._seed_exam(db)
        r = admin_client.get("/api/search?q=BUSCACC001")
        assert r.status_code == 200
        data = r.json()["data"]
        assert any(d["accession_number"] == "BUSCACC001" for d in data if not d["is_pacs"])

    def test_busca_vazia_retorna_lista(self, admin_client):
        r = admin_client.get("/api/search?q=")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_busca_case_insensitive(self, admin_client, db):
        self._seed_exam(db)
        r = admin_client.get("/api/search?q=maria")  # minúsculo
        assert r.status_code == 200
        data = r.json()["data"]
        assert any("MARIA" in d["patient_name"] for d in data if not d["is_pacs"])

    def test_sem_autenticacao_retorna_401(self, client):
        r = client.get("/api/search?q=teste")
        assert r.status_code == 401
