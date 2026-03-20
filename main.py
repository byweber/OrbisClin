"""
main.py — Ponto de entrada da aplicação OrbisClin.
Localização: raiz do projeto (mesmo nível de app/)
"""
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.models import User
from app.core.security import get_password_hash
from app.routers import auth, users, exams, stats, timeline, audit, reports, system

settings = get_settings()
limiter   = Limiter(key_func=get_remote_address)


def _create_default_admin() -> None:
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                full_name="ADMINISTRADOR",
                role="ADMIN",
                matricula="0001",
                birth_date="1990-01-01",
                is_active=True,
            ))
            db.commit()
            print("✅ Usuário admin criado (senha: admin123 — altere imediatamente!)")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _create_default_admin()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} — ONLINE")
    yield


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")

# ── Rate limiting ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── Middlewares ────────────────────────────────────────────────────────────────
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0", "*"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def inject_app_version(request: Request, call_next):
    request.state.app_version = settings.APP_VERSION
    return await call_next(request)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(exams.router)
app.include_router(stats.router)
app.include_router(timeline.router)
app.include_router(audit.router)
app.include_router(reports.router)
app.include_router(system.router)

# ── Páginas HTML ───────────────────────────────────────────────────────────────
@app.get("/login",     response_class=HTMLResponse)
async def login_page(request: Request):    return templates.TemplateResponse("login.html",    {"request": request})
@app.get("/",          response_class=HTMLResponse)
async def home(request: Request):          return templates.TemplateResponse("home.html",      {"request": request})
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):     return templates.TemplateResponse("dashboard.html", {"request": request})
@app.get("/admin",     response_class=HTMLResponse)
async def admin_page(request: Request):    return templates.TemplateResponse("admin.html",     {"request": request})
@app.get("/audit",     response_class=HTMLResponse)
async def audit_page(request: Request):    return templates.TemplateResponse("audit.html",     {"request": request})
@app.get("/reports",   response_class=HTMLResponse)
async def reports_page(request: Request):  return templates.TemplateResponse("reports.html",   {"request": request})
@app.get("/timeline",  response_class=HTMLResponse)
async def timeline_page(request: Request): return templates.TemplateResponse("timeline.html",  {"request": request})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
