# Nexus 🧩  
### Sistema Open Source de Gestão de Exames e Laudos Clínicos

![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
![Open Source](https://img.shields.io/badge/open--source-community--driven-orange.svg)

---

## 🌍 Sobre o Projeto

**Nexus** é um projeto **open source** focado na gestão de exames médicos e laudos digitais (PDF), criado para servir como base para clínicas, hospitais, laboratórios ou projetos educacionais que demandam **controle de acesso**, **auditoria**, **segurança** e **simplicidade de implantação**.

O projeto nasce com a filosofia de:
- Código simples, legível e auditável
- Fácil adaptação para diferentes realidades
- Incentivo à colaboração da comunidade

---

## ✨ Principais Recursos

### 🔐 Autenticação & Segurança
- Autenticação baseada em **JWT**
- Perfis de acesso (RBAC):
  - `ADMIN`
  - `MEDICO`
  - `VIEWER`
- Hash seguro de senhas
- Registro de auditoria para ações críticas

### 📂 Gestão de Arquivos Clínicos
- Upload seguro de PDFs
- Validação de integridade por *magic number*
- Associação de exames a pacientes
- Visualização direta no navegador

### 📊 Administração
- Dashboard com métricas de uso
- Scripts utilitários para:
  - Backup
  - Reset de ambiente
  - Seed de dados para testes

---

## 🧱 Arquitetura & Stack

| Camada   | Tecnologia |
|--------|------------|
| Backend | Python + FastAPI |
| ORM    | SQLAlchemy |
| Banco  | SQLite (default) / PostgreSQL |
| Frontend | HTML + Tailwind CSS |

O projeto foi desenhado para ser **modular**, facilitando a troca de banco de dados ou a adição de novos módulos.

---

## 🚀 Como Executar Localmente

### 📌 Requisitos
- Python **3.8+**
- Git

---

### 📥 Clone o repositório

```bash
git clone https://github.com/byweber/nexus.git
cd nexus
```

---

### 🐍 Ambiente Virtual

```bash
python -m venv venv
# Linux / Mac
source venv/bin/activate
# Windows
.\venv\Scripts\activate
```

---

### 📦 Dependências

```bash
pip install -r requirements.txt
```

---

### ⚙️ Configuração (.env)

Crie um arquivo `.env` na raiz do projeto:

```
ENVIRONMENT=development
SECRET_KEY=change-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

DATABASE_URL=sqlite:///./Nexus/database.db
STORAGE_PATH=./Nexus/storage
```

---

### ▶️ Executar

```bash
python main.py
```

A aplicação ficará disponível em:

➡️ `http://localhost:8000`

Credenciais iniciais:
- Usuário: `admin`
- Senha: `admin123`

---

## 🧪 Scripts Úteis

| Script | Função |
|------|--------|
| `backup.py` | Backup completo do sistema |
| `reset_system.py` | Restaura estado inicial |
| `robot_seeder.py` | Popula dados fictícios |

---

## 🤝 Contribuindo

Contribuições são muito bem-vindas!  
Você pode ajudar de várias formas:

- Reportando bugs
- Sugerindo melhorias
- Enviando Pull Requests
- Melhorando documentação

Antes de contribuir:
1. Fork o projeto
2. Crie uma branch
3. Faça suas alterações
4. Abra um Pull Request 🚀

---

## 🛡️ Licença

Este projeto é distribuído sob a licença **GPL-3.0**.  
Você é livre para usar, modificar e redistribuir, respeitando os termos da licença.

---

## ❤️ Comunidade

Se você usa o Nexus em produção, estudos ou testes, considere compartilhar feedback.  
Projetos open source crescem com colaboração!

> “Código aberto não é só código — é comunidade.”

---

📌 **Maintainer:** Lucas Weber  
📦 **Repositório:** https://github.com/byweber/Nexus