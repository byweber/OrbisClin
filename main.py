import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from database import engine, Base, SessionLocal
from models import User
from security import get_password_hash
from routers import auth, users, exams, stats

# Cria tabelas no banco
Base.metadata.create_all(bind=engine)

def create_default_users():
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        print("--- CRIANDO ADMIN PADRÃO ---")
        db.add(User(username="admin", hashed_password=get_password_hash("admin123"), full_name="Administrador", role="ADMIN", matricula="0001", birth_date="1990-01-01", is_active=True))
        db.commit()
    db.close()

APP_VERSION = "7.6-SECURE"
app = FastAPI(title="Nexus", version=APP_VERSION)
templates = Jinja2Templates(directory="templates")

# Proteções de Infraestrutura
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0", "*"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"])

@app.middleware("http")
async def add_global_vars(request: Request, call_next):
    request.state.app_version = APP_VERSION
    return await call_next(request)

# Rotas da API
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(exams.router)
app.include_router(stats.router)

# Rotas de Frontend (Apenas Sistema Interno)
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request): return templates.TemplateResponse("login.html", {"request": request})
@app.get("/", response_class=HTMLResponse)
async def home(request: Request): return templates.TemplateResponse("index.html", {"request": request})
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request): return templates.TemplateResponse("dashboard.html", {"request": request})
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request): return templates.TemplateResponse("admin.html", {"request": request})
@app.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request): return templates.TemplateResponse("audit.html", {"request": request})
@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request): return templates.TemplateResponse("reports.html", {"request": request})

if __name__ == "__main__":
    create_default_users()
    print(f"Nexus v{APP_VERSION} - ONLINE (Porta 8000)")

    uvicorn.run(app, host="0.0.0.0", port=8000)