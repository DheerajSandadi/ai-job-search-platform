# AI Job Search Platform — CLAUDE.md

## Overview
Autonomous job search platform: FastAPI backend + Next.js 15 frontend.
Owner: Dheeraj Reddy

## Monorepo layout
- `backend/` — Python 3.11 FastAPI app (virtualenv at `backend/.venv`)
- `frontend/` — Next.js 15 app (dependencies in `frontend/node_modules`)

## Running locally

### Backend
```bash
cd backend
source .venv/bin/activate
cp .env.example .env          # fill in real keys
uvicorn main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8001
npm run dev                         # http://localhost:3001
```

### Gmail Setup
1. Go to Google Cloud Console → Create project → Enable Gmail API
2. Create OAuth 2.0 credentials (Web application type)
3. Add authorized redirect URI: `http://localhost:8001/auth/gmail/callback`
4. Copy credentials into `backend/.env`:
   ```
   GMAIL_CLIENT_ID=your_client_id
   GMAIL_CLIENT_SECRET=your_client_secret
   GMAIL_REDIRECT_URI=http://localhost:8001/auth/gmail/callback
   GMAIL_USER_EMAIL=your@gmail.com
   ```
5. Start backend, then open `http://localhost:8001/auth/gmail/login`
6. Complete Google consent — tokens are saved to Supabase settings table automatically

## Stack rules
- Backend: Python 3.11, FastAPI, Pydantic v2, structlog (never print()), tenacity for retries
- Frontend: Next.js 15 App Router, TypeScript strict, Tailwind + shadcn/ui, Axios, SWR
- All pinned versions are in `backend/requirements.txt` — do not change them
- Install backend deps with `--no-deps` flag if pip resolver conflicts occur (known issue with langchain-core version pinning)

## Key files
- `backend/models/schemas.py` — all Pydantic models (source of truth for data shapes)
- `frontend/src/types/index.ts` — TypeScript interfaces (mirror schemas.py exactly)
- `frontend/src/lib/api.ts` — all API calls (Axios, typed)
- `backend/orchestrator/state.py` — LangGraph PipelineState TypedDict
- `backend/supabase_schema.sql` — DB schema (run in Supabase SQL editor)

## Agent system (stub, implement next)
Five CrewAI/LangGraph agents under `backend/agents/`:
- `job_scout` — discovers jobs via Apify, Indeed, Dice MCP
- `recruiter` — finds recruiters via Vibe Prospecting + Apollo
- `resume` — tailors resumes with Claude Sonnet
- `outreach` — drafts and sends recruiter emails via Gmail
- `inbox` — classifies replies and drafts responses

## Pipelines
- `morning_pipeline.py` — runs job_scout → resume → outreach at 6am
- `inbox_pipeline.py` — processes new Gmail messages
- `retry_pipeline.py` — retries failed applications at 9am

## Application Workflow (Manual Apply)

1. Morning pipeline discovers + scores jobs
2. Claude tailors resume for jobs scoring >= 0.65
3. Applications appear in `/applications` dashboard with `status: pending`
4. User reviews resume diff → clicks **Approve & Open Job**
   → job URL opens in new tab automatically
5. User fills and submits form on employer site
6. User clicks **Mark as Applied** → status becomes `applied`
7. `submitted_at` timestamp recorded in Supabase
8. Analytics updated: `applications_submitted + 1`

Status lifecycle: `pending → approved → applied` or `pending → rejected`

## API prefix
All endpoints: `GET/POST /api/v1/{resource}`
Gmail webhook: `POST /webhooks/gmail`
