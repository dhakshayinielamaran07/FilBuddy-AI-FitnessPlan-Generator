# FitBuddy – AI Fitness Plan Generator

FitBuddy is a FastAPI + Jinja2 web application that creates personalized 7-day workout plans and nutrition/recovery tips with Gemini, stores users/plans in SQLite, and lets users regenerate a plan from feedback.

## Features

- Personalized 7-day workout plan
- Goal and workout-intensity customization
- Fast nutrition/recovery tip generation
- Feedback-based plan regeneration
- SQLite persistence with SQLAlchemy
- Admin dashboard for users and plans
- JSON REST API and browser UI
- Gemini API integration through the current `google-genai` SDK
- Configurable model names through `.env`
- Demo/mock AI mode for testing without an API key
- Input validation and friendly error handling

## Architecture

```text
Browser / REST Client
        |
        v
   FastAPI routes
        |
   +----+----------------+
   |                     |
Database service      Gemini service
   |                     |
SQLite + SQLAlchemy   Gemini API
   |                     |
   +----------+----------+
              |
          Jinja2 UI
```

## Important health note

FitBuddy provides general wellness information, not medical diagnosis or treatment. Users with injuries, chronic conditions, pregnancy, or other medical concerns should consult a qualified healthcare professional before following a workout or nutrition plan.

## Quick start

### Windows PowerShell

```powershell
cd FitBuddy
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Open `.env`, set `GEMINI_API_KEY`, then run:

```powershell
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

API docs: http://127.0.0.1:8000/docs

### Windows CMD

```bat
cd FitBuddy
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

### macOS/Linux

```bash
cd FitBuddy
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## No API key testing

Set this in `.env`:

```env
MOCK_AI=true
```

The application then returns deterministic demo workout/nutrition responses so you can test the full frontend, database, routes, feedback flow, and admin dashboard without calling Gemini.

## API endpoints

- `GET /` – web home page
- `POST /generate-workout` – HTML form workflow
- `POST /submit-feedback` – HTML feedback workflow
- `GET /view-all-users` – admin dashboard
- `DELETE /admin/users/{user_id}` – delete a user and their plans
- `GET /health` – health check
- `POST /api/plans` – JSON plan generation
- `POST /api/plans/{user_id}/feedback` – JSON plan update
- `GET /api/users` – list users/plans
- `GET /api/users/{user_id}` – get one user and plans
- `DELETE /api/users/{user_id}` – delete a user

## Project structure

```text
FitBuddy/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── routes.py
│   ├── schemas.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── gemini_service.py
│   ├── static/
│   │   └── css/
│   │       └── style.css
│   └── templates/
│       ├── all_users.html
│       ├── base.html
│       ├── index.html
│       └── result.html
├── tests/
│   └── test_app.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```
