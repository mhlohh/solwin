# Solwin - AI Support & Threat Intelligence (Backend)

The backend foundation for **Solwin**, an AI-powered customer support and threat intelligence platform designed to detect threats (such as phishing), evaluate combined operational risks, and assist support teams in real time.

---

## 🛠 Technology Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+)
- **Server**: [Uvicorn](https://www.uvicorn.org/) (ASGI)
- **Configuration & Validation**: [Pydantic v2](https://docs.pydantic.dev/) & [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **ORM & Database**: [SQLAlchemy 2.x](https://docs.sqlalchemy.org/) & [PostgreSQL](https://www.postgresql.org/)
- **Database Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Testing**: [pytest](https://docs.pytest.org/) & [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- **Code Quality**: [Ruff](https://docs.astral.sh/ruff/) & [Black](https://black.readthedocs.io/)

---

## 📁 Project Structure

```text
solwin-backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entrypoint, lifespan, health check
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── router.py    # Central API v1 router
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Pydantic Settings and env loader
│   │   ├── database.py      # SQLAlchemy 2.x engine, SessionLocal, Base, get_db
│   │   └── logging.py       # Standard logging setup
│   │
│   ├── models/              # SQLAlchemy declarative models (future features)
│   │   └── __init__.py
│   │
│   ├── schemas/             # Pydantic request/response schemas (future features)
│   │   └── __init__.py
│   │
│   └── services/            # Domain and business logic services (future features)
│       └── __init__.py
│
├── tests/
│   ├── __init__.py
│   └── test_health.py       # Health check automated tests
│
├── alembic/                 # Migration scripts and environment configuration
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── alembic.ini              # Alembic configuration file
├── requirements.txt         # Project dependencies
├── .env.example             # Example environment variables
├── .gitignore
├── pyproject.toml           # Ruff, Black, and pytest configurations
└── README.md
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `APP_NAME` | Name of the FastAPI application | `"Solwin API"` |
| `APP_ENV` | Environment (`development`, `testing`, `production`) | `"development"` |
| `DEBUG` | Enable/disable debug mode and verbose SQL logs | `True` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/solwin_db` |
| `GEMINI_API_KEY` | Google Gemini API Key for AI capabilities | `"your-gemini-api-key-here"` |
| `JWT_SECRET_KEY` | Secret key for JWT auth tokens | `"replace-this-with-a-secure-random-secret-key-in-production"` |

---

## 🚀 Local Setup & Installation

### 1. Create and Activate Virtual Environment

```bash
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

---

## ▶️ Running the Application

Start the development server with Uvicorn:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📖 API Documentation & Swagger

Once the application is running, access the interactive documentation:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 🧪 Testing & Code Quality

### Running Tests

```bash
python -m pytest
```

### Checking Linting (Ruff)

```bash
python -m ruff check .
```

### Checking Code Formatting (Black)

```bash
python -m black --check .
```

### Formatting Code

```bash
python -m black .
```

---

## 🗄 Database Migrations (Alembic)

Alembic is configured to automatically bind `DATABASE_URL` from your settings and discover models from `app.core.database.Base`.

To generate a new migration after defining models in `app/models/`:

```bash
python -m alembic revision --autogenerate -m "create_initial_tables"
```

To run pending migrations:

```bash
python -m alembic upgrade head
```
