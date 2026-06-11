# AI Job Search Platform

Autonomous AI-powered job search and application platform for Dheeraj Reddy.

## What it does
- Discovers new job postings every morning via Apify, LinkedIn, Indeed, Dice
- Scores jobs against your resume using ATS + semantic analysis (Claude Haiku)
- Tailors your resume for each high-scoring job (Claude Sonnet)
- Presents approvals via dashboard — one click to approve/reject
- Applies to approved jobs via Playwright browser automation
- Finds and cold-emails recruiters via Vibe Prospecting + Apollo
- Monitors Gmail replies and drafts responses automatically

## Quick start

### Prerequisites
- Python 3.11
- Node.js 18+
- Supabase project
- Anthropic API key

### Backend
```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install --no-deps -r requirements.txt
cp .env.example .env   # fill in all keys
uvicorn main:app --reload --port 8001
```

### Gmail OAuth
1. Google Cloud Console → Enable Gmail API → Create Web OAuth credentials
2. Add redirect URI: `http://localhost:8001/auth/gmail/callback`
3. Set `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_USER_EMAIL` in `backend/.env`
4. Start backend, open `http://localhost:8001/auth/gmail/login`, complete consent
5. Tokens are auto-saved to Supabase — check status at `http://localhost:8001/auth/gmail/status`

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3001

### Database
Run `backend/supabase_schema.sql` in your Supabase SQL editor.

## Architecture

```
frontend (Next.js 15) ──► backend (FastAPI) ──► LangGraph Orchestrator
                                    │                    │
                               Supabase DB          CrewAI Agents
                               Gmail API            ├── job_scout
                               Playwright           ├── recruiter
                               Apify               ├── resume
                               Apollo/Vibe          ├── outreach
                                                    └── inbox
```
