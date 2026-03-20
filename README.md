# OrbisClin

Sistema web de gestão de imagens e documentos clínicos com integração ao Orthanc PACS.
Implantado de forma self-hosted em hospitais, clínicas e redes de saúde.

## Stack

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.12 + FastAPI + Uvicorn |
| ORM | SQLAlchemy |
| Banco | SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT em httponly cookie + slowapi rate limiting |
| Tasks | Celery + Redis (extração de texto de PDFs) |
| Frontend | Jinja2 + Tailwind CSS + Chart.js |

## Estrutura

```
orbisclin/
├── main.py                  # Ponto de entrada FastAPI
├── reset_system.py          # Reset de banco e storage
├── requirements.txt
├── pytest.ini
├── .env                     # NÃO versionar
├── .env.example
├── app/
│   ├── core/
│   │   ├── config.py        # Settings via pydantic-settings
│   │   ├── database.py      # Engine SQLAlchemy
│   │   ├── models.py        # User, Patient, ExamSession, ExamFile, AuditLog
│   │   ├── security.py      # JWT, bcrypt, cookie helpers
│   │   ├── worker.py        # Celery tasks
│   │   └── backup.py        # Geração de backup zip
│   ├── routers/
│   │   ├── auth.py          # POST /token, /api/auth/logout
│   │   ├── users.py         # CRUD /api/users/
│   │   ├── exams.py         # /api/upload, /api/search, /view/{id}
│   │   ├── stats.py         # GET /api/stats
│   │   ├── audit.py         # GET /api/audit
│   │   ├── reports.py       # GET /api/reports
│   │   ├── system.py        # GET /api/system/backup
│   │   └── timeline.py      # GET /api/timeline/{patient_id}
│   └── templates/
│       ├── base.html
│       ├── login.html
│       ├── home.html
│       ├── dashboard.html
│       ├── admin.html
│       ├── audit.html
│       ├── reports.html
│       └── timeline.html
└── tests/
    ├── conftest.py
    ├── test_auth.py
    ├── test_users.py
    ├── test_security.py
    ├── test_exams.py
    └── test_audit.py
```

## Instalação

```bash
git clone <repo>
cd orbisclin
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

Crie o arquivo `.env` a partir do `.env.example` e defina `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Execução

```bash
python main.py
```

Acesse: `http://localhost:8000`  
Login padrão: `admin` / `admin123` — **altere imediatamente.**

## Testes

```bash
pytest
```

## Deploy (Windows Service via NSSM)

```bat
nssm install OrbisClin "C:\Python312\python.exe" "-m uvicorn main:app --host 0.0.0.0 --port 8000"
nssm set OrbisClin AppDirectory "C:\orbisclin"
nssm start OrbisClin
```

---

**Desenvolvido por:** Lucas Weber  
**Licença:** GPL-3.0
