# Bill Generator Backend API

A production-ready **FastAPI** backend for comprehensive bill management, payment tracking, and automated reminders.

## 🚀 Tech Stack

| Component | Technology |
|---|---|
| Framework | FastAPI 0.111 |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 |
| Migrations | Alembic |
| Auth | JWT (python-jose) + bcrypt |
| Task Queue | Celery + Redis |
| Email | aiosmtplib (async SMTP) |
| PDF | ReportLab |
| SMS | Twilio |
| Testing | pytest + httpx |

## 📁 Project Structure

```
bill_generation_backend/
├── app/
│   ├── api/v1/          # Route handlers
│   │   ├── auth.py      # Authentication endpoints
│   │   ├── bills.py     # Bill CRUD endpoints
│   │   ├── payments.py  # Payment endpoints
│   │   ├── reminders.py # Reminder endpoints
│   │   └── reports.py   # Analytics & export endpoints
│   ├── middleware/
│   │   └── auth_middleware.py  # JWT dependency injection
│   ├── models/          # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── bill.py
│   │   ├── payment.py
│   │   └── reminder.py
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic layer
│   │   ├── auth_service.py
│   │   ├── bill_service.py
│   │   ├── payment_service.py
│   │   ├── reminder_service.py
│   │   ├── email_service.py
│   │   ├── pdf_service.py
│   │   ├── sms_service.py
│   │   └── report_service.py
│   ├── tasks/           # Celery background tasks
│   │   ├── reminder_tasks.py
│   │   └── report_tasks.py
│   ├── celery_app.py    # Celery + Beat configuration
│   ├── config.py        # Settings via pydantic-settings
│   ├── database.py      # SQLAlchemy engine & session
│   └── main.py          # FastAPI application
├── alembic/             # Database migrations
├── scripts/
│   └── seed_data.py     # Demo data seeder
├── tests/               # pytest test suite
├── .env.example         # Environment template
├── docker-compose.yml   # Full stack containers
├── Dockerfile
└── requirements.txt
```

## ⚡ Quick Start

### 1. Clone & Setup

```bash
git clone <repo-url>
cd bill_generation_backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
# Edit .env with your credentials
```

### 3. Start Docker Services (PostgreSQL + Redis)

```bash
docker-compose up postgres redis -d
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Seed Demo Data (Optional)

```bash
python scripts/seed_data.py
# Login: demo@billgenerator.com / DemoPass123
```

### 6. Start the API Server

```bash
uvicorn app.main:app --reload
```

API is now running at **http://localhost:8000**
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 🐳 Full Docker Stack

```bash
docker-compose up --build
```

Starts: PostgreSQL, Redis, API, Celery Worker, Celery Beat

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login → get tokens |
| POST | `/api/v1/auth/refresh-token` | Refresh access token |
| POST | `/api/v1/auth/forgot-password` | Request password reset |
| POST | `/api/v1/auth/reset-password` | Reset password |
| GET | `/api/v1/auth/verify-email` | Verify email |
| GET | `/api/v1/auth/me` | Get profile |

### Bills
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/bills/` | Create bill |
| GET | `/api/v1/bills/` | List bills (paginated) |
| GET | `/api/v1/bills/{id}` | Get bill by ID |
| PUT | `/api/v1/bills/{id}` | Update bill |
| DELETE | `/api/v1/bills/{id}` | Delete bill |
| POST | `/api/v1/bills/{id}/mark-paid` | Mark as paid |
| GET | `/api/v1/bills/overdue/list` | List overdue bills |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/payments/` | Record payment |
| GET | `/api/v1/payments/` | List payments |
| GET | `/api/v1/payments/{id}` | Get payment |
| PUT | `/api/v1/payments/{id}` | Update payment |
| DELETE | `/api/v1/payments/{id}` | Delete payment |
| GET | `/api/v1/payments/bill/{bill_id}` | Get bill's payments |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/reports/dashboard` | Dashboard stats |
| GET | `/api/v1/reports/bills` | Bill breakdown |
| GET | `/api/v1/reports/payments` | Payment analysis |
| GET | `/api/v1/reports/analytics` | Full analytics |
| GET | `/api/v1/reports/export?format=pdf` | Export PDF/CSV |

## 🧪 Running Tests

```bash
pytest                    # Run all tests
pytest tests/ -v          # Verbose output
pytest tests/test_auth_api.py  # Single file
pytest --cov=app          # With coverage (needs pytest-cov)
```

## ⏰ Celery Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `send_bill_reminders` | Every 5 min | Send pending email/SMS reminders |
| `mark_overdue_bills` | Every hour | Update bills past due date to OVERDUE |
| `generate_monthly_report` | 1st of month, 8am UTC | Email PDF reports to users |
| `clean_old_data` | Weekly (Sunday) | Delete sent reminders older than 90 days |

## 🔐 Security Features
- bcrypt password hashing
- JWT access tokens (30 min) + refresh tokens (7 days)
- Email verification flow
- Password reset tokens (1 hour expiry)
- SQL injection prevention via SQLAlchemy ORM
- CORS configuration
- Input validation via Pydantic
