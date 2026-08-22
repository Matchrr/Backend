# Matchr Backend

FastAPI service for candidates, jobs, applications, growth plans, networking events, and OAuth integrations. Persists to Supabase (`pgvector`) and calls the `ai-service` for agent work.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Routes

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/api/health` | Liveness |
| POST | `/api/candidates` | Create / seed candidate |
| POST | `/api/candidates/resume` | Resume PDF upload |
| GET | `/api/candidates/me` | Grounded profile |
| GET | `/api/jobs/matches` | Ranked job matches + Fit Scorecard |
| POST | `/api/applications` | Start a dossier / application |
| GET | `/api/growth/plan` | Skill-gap growth plan |
| GET | `/api/events/matches` | Top compatible networking events |
| GET | `/api/integrations` | LinkedIn / Gmail connection status |
| POST | `/api/outreach/draft` | Cold-email draft (via ai-service) |
| POST | `/api/outreach/send` | Send via connected Gmail (user-approved) |
