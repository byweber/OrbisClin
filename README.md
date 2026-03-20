# OrbisClin

Sistema web de gestão de imagens e documentos clínicos com integração ao Orthanc PACS.
Implantado de forma self-hosted em hospitais, clínicas e redes de saúde.

## Stack

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.12 + FastAPI + Uvicorn |
| ORM | SQLAlchemy + Alembic (migrations) |
| Banco | SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT em httponly cookie + slowapi rate limiting |
| Tasks | Celery + Redis (extração de texto de PDFs) com fallback síncrono |
| Frontend | Jinja2 + Tailwind CSS + Chart.js |
| Deploy | Windows Service via NSSM |

## Funcionalidades

- **Busca de exames** — por paciente, ID, número de acesso ou texto extraído de PDFs
- **Upload de exames** — PDF para todos os procedimentos; PDF/JPG/PNG para Dermatologia e Avaliação de Feridas
- **Lookup automático** — ao digitar ID do paciente ou número de acesso, os dados são preenchidos automaticamente
- **Timeline evolutiva** — visualização cronológica de imagens por paciente (Dermatologia e Feridas)
- **Viewer de imagens** — slideshow com miniaturas, navegação por teclado e zoom
- **Comparação lado a lado** — dois painéis independentes para comparar sessões de datas diferentes
- **Anotações clínicas imutáveis** — registro de evolução clínica por imagem com histórico completo (autor + data/hora)
- **Dashboard gerencial** — gráficos de uploads e distribuição por tipo de procedimento
- **Relatórios** — filtráveis por período, tipo e solicitante; exportação CSV e PDF
- **Auditoria** — trilha completa de ações com hash de integridade
- **Backup** — geração e download de backup completo via interface
- **Gestão de usuários** — CRUD com roles ADMIN, MEDICO e VIEWER

## Estrutura

```
OrbisClin/
├── main.py                  # Ponto de entrada FastAPI
├── reset_system.py          # Reset de banco e storage (desenvolvimento)
├── alembic.ini              # Configuração do Alembic
├── requirements.txt
├── pytest.ini
├── .env                     # NÃO versionar
├── .env.example
├── migrations/              # Migrations Alembic
│   └── env.py
├── app/
│   ├── core/
│   │   ├── config.py        # Settings via pydantic-settings
│   │   ├── database.py      # Engine SQLAlchemy
│   │   ├── models.py        # User, Patient, ExamSession, ExamFile, ImageNote, AuditLog
│   │   ├── security.py      # JWT, bcrypt, cookie helpers
│   │   ├── worker.py        # Celery tasks (extração de texto PDF)
│   │   └── backup.py        # Geração de backup zip
│   ├── routers/
│   │   ├── auth.py          # POST /token, /api/auth/logout
│   │   ├── users.py         # CRUD /api/users/ + GET /api/users/me
│   │   ├── exams.py         # /api/upload, /api/search, /view/{id}
│   │   │                    # /api/files/{id}/notes (GET + POST)
│   │   ├── stats.py         # GET /api/stats  (ADMIN)
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
│       ├── timeline.html
│       └── viewer.html      # Slideshow + comparação lado a lado
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
git clone https://github.com/byweber/OrbisClin.git
cd OrbisClin
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

Crie o arquivo `.env` a partir do `.env.example` e defina `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Primeira execução

```bash
python reset_system.py
```

Quando solicitado, confirme com `RESET`. Isso cria o banco, as tabelas e o usuário administrador padrão.

## Execução

```bash
python main.py
```

Acesse: `http://localhost:8000`
Login padrão: `admin` / `admin123` — **altere imediatamente após o primeiro acesso.**

Para extração de texto de PDFs (opcional), suba o worker Celery em terminal separado:

```bash
celery -A app.core.worker.celery_app worker --loglevel=info --pool=solo
```

> O upload funciona normalmente sem o Celery — a extração de texto cai para modo síncrono automaticamente.

## Migrations (Alembic)

Para aplicar alterações de schema sem resetar o banco:

```bash
# Gerar migration após alterar models.py
alembic revision --autogenerate -m "descricao_da_mudanca"

# Aplicar
alembic upgrade head
```

## Testes

```bash
set TESTING=1   # Windows
pytest
```

## Roles e permissões

| Role | Permissões |
|------|------------|
| ADMIN | Acesso total — dashboard, admin, audit, relatórios, backup, CRUD de usuários |
| MEDICO | Upload e busca de exames, criação de anotações clínicas |
| VIEWER | Busca e leitura de exames e anotações — sem upload |

## Procedimentos e tipos de arquivo aceitos

| Procedimento | Arquivos aceitos |
|---|---|
| ECG, EEG, HOLTER, AUDIOMETRIA | Apenas PDF |
| DERMATOLOGIA, AVALIAÇÃO DE FERIDAS | PDF, JPG, PNG (múltiplos arquivos) |

## Deploy (Windows Service via NSSM)

```bat
nssm install OrbisClin "C:\Python312\python.exe" "-m uvicorn main:app --host 0.0.0.0 --port 8000"
nssm set OrbisClin AppDirectory "C:\OrbisClin"
nssm start OrbisClin
```

## Roadmap

- [ ] Nginx + HTTPS (produção)
- [ ] Conversão DICOM + integração Orthanc PACS
- [ ] Timeline híbrida (local + fallback Orthanc)
- [ ] StoneWebViewer para análise diagnóstica formal
- [ ] PostgreSQL (concorrência em produção)
- [ ] 2FA para ADMIN (TOTP)
- [ ] Notificações ao médico solicitante após upload

---

**Desenvolvido por:** Lucas Weber
**Repositório:** https://github.com/byweber/OrbisClin
**Licença:** GPL-3.0
