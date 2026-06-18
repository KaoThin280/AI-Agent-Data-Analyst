================================================================================
                       STEAM GAME DATA ANALYST - README
================================================================================

PROJECT OVERVIEW
================================================================================
Steam Game Data Analyst is a full-stack web application that combines an LLM,
a read-only Supabase PostgreSQL database (Steam games, users, reviews), an E2B
Python sandbox, and interactive Plotly charts.

Users can ask natural-language questions about the connected sample data
without uploading anything, and can also drop in their own CSV/Excel files
for one-off analysis. The AI agent can describe the data, run read-only SQL
queries through a dedicated `QUERY_DB` tool, and execute Python visualisation
code in a sandbox.

The system uses a strict AI-System communication protocol: the LLM replies
with `Response to user / Request system / Code`, and the backend services
follow the request until the LLM is ready to answer. Every step is emitted
as a workflow event so the UI can show a live progress panel.


KEY FEATURES
================================================================================
1. PRE-LOADED SAMPLE DATA
   - A local time-series CSV (sample_timeseries.csv) is registered on
     startup so there is always something to ask about.
   - Read-only virtual views over the connected Supabase Steam database
     (db.games, db.users, db.reviews) appear in the sidebar with live
     row counts.
   - One-click "Tell me about this data" button on every sample card.

2. NATURAL LANGUAGE CHAT INTERFACE
   - Plain-English chat with the AI about any of the registered tables.
   - Live workflow panel that shows what the backend is currently doing
     (Calling AI, Reading data context, Querying database, Running code,
     Finalising).
   - Per-step retry and error reporting.

3. DATABASE TOOL (LLM can query Supabase)
   - The model emits `Request system: QUERY_DB` with a JSON payload
     describing the table, columns, filters, ordering, and limit.
   - The backend runs a safe, read-only SQLAlchemy query against Supabase
     and feeds the result back to the LLM as additional context.
   - Aggregations (count, avg, min, max, sum) are supported.

4. E2B CODE EXECUTION
   - For visualisations and statistical analysis the model emits
     `Request system: E2B_EXE` with raw Python code.
   - Code runs in a fresh E2B sandbox, generated CSV/HTML/PNG files
     are downloaded back to the backend and shown in the right panel.

5. FILE UPLOAD (OPTIONAL)
   - CSV/XLS/XLSX files up to 100 MB can still be uploaded for ad-hoc
     analysis. The structured workflow treats them like any other table.

6. INTERACTIVE VISUALISATIONS
   - Auto-generated Plotly charts (HTML) and PNG images.
   - Manual chart builder for custom visualisations on uploaded data.

7. LANDING EXPERIENCE
   - Static greeting, system notes, and sample-data description on first
     visit (no backend interaction required to render).
   - Live server-status badge in the top bar with the free-tier warm-up
     warning ("first request can take 30-60 seconds").

8. USER FEEDBACK
   - Submit reviews and ratings via /reviews endpoint.

9. API SECURITY
   - X-API-Key authentication for all protected endpoints.
   - Public landing endpoints (/api/intro, /api/status, /api/sample-data/*,
     /health) do not require the API key, so the first paint is fast.


ARCHITECTURE
================================================================================

  ┌────────────────────┐    X-API-Key    ┌────────────────────────────┐
  │  Vercel (Free)     │ ──────────────▶ │  Render (Free)             │
  │  React + Vite SPA  │                 │  FastAPI app.main:app      │
  │                    │                 │                            │
  │  - IntroPanel      │                 │  Routers:                  │
  │  - ChatInterface   │                 │   /api/intro (public)      │
  │  - ServerStatus    │                 │   /api/status (public)     │
  │  - WorkflowProg.   │                 │   /api/sample-data/* (pub) │
  │  - Sidebar/Upload  │                 │   /health (public)         │
  │                    │                 │   /upload, /chat, /files,  │
  └────────────────────┘                 │   /tables, /reviews       │
                                         │                            │
                                         │  Services:                 │
                                         │   LLMService (OpenRouter) │
                                         │   DBService (Supabase)    │
                                         │   E2BService (sandbox)     │
                                         │   SampleDataService        │
                                         │   StructuredWorkflow       │
                                         └────────────┬───────────────┘
                                                      │ asyncpg
                                                      ▼
                                         ┌────────────────────────────┐
                                         │  Supabase PostgreSQL       │
                                         │  (Free tier)               │
                                         │                            │
                                         │  games, users, reviews     │
                                         │  (+ RBAC tables)           │
                                         └────────────────────────────┘


PROJECT STRUCTURE
================================================================================

ROOT DIRECTORY
│
├── README.txt                       # This file
├── .gitignore                       # Repo-level ignore rules
│
├── back_end/                        # FastAPI backend
│   ├── requirements.txt             # Python dependencies
│   ├── render.yaml                  # One-click Render Blueprint
│   ├── SCHEMA_DOCUMENTATION.md      # DB schema reference
│   ├── sample_timeseries.csv        # Bundled CSV sample
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   │
│   │   ├── api/routers/
│   │   │   ├── info.py              # /api/intro, /api/status (public)
│   │   │   ├── chat.py              # /chat (the workflow)
│   │   │   ├── upload.py            # /upload (CSV/Excel ingest)
│   │   │   ├── manual_plot.py       # /tables/{id} (manual charts)
│   │   │   ├── reviews.py           # /reviews
│   │   │   ├── download.py          # /files, /files/{name}
│   │   │   └── db/sessions.py       # SQLAlchemy async engine (Supabase)
│   │   │
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic settings
│   │   │   └── security.py          # X-API-Key auth
│   │   │
│   │   ├── services/
│   │   │   ├── llm_service.py           # OpenRouter client
│   │   │   ├── data_service.py          # DataContext extraction
│   │   │   ├── e2b_service.py           # (legacy agentic workflow)
│   │   │   ├── db_service.py            # Supabase read-only tool
│   │   │   ├── session_service.py       # In-memory session state
│   │   │   ├── sample_data_service.py   # Registers sample tables
│   │   │   └── structured_workflow.py   # AI <-> System protocol loop
│   │   │
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── steam.py             # Game, SteamUser, Review
│   │   │   └── user.py              # AppUser, Role, Permission
│   │   │
│   │   ├── db/
│   │   │   └── base.py              # SQLAlchemy declarative base
│   │   │
│   │   └── utils/
│   │       └── response_formatter.py
│   │
│   ├── temp_data/                   # Generated files (gitignored)
│   └── reviews.txt                  # User feedback (gitignored)
│
└── frontend/                        # React + Vite frontend
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── eslint.config.js
    ├── index.html
    ├── .env                         # VITE_API_BASE_URL + secret (gitignored)
    │
    ├── public/
    └── src/
        ├── main.jsx
        ├── App.jsx
        │
        ├── api/axiosClient.js       # Axios + X-API-Key injection
        ├── services/api.js          # API client (chat, intro, status)
        ├── store/useAppStore.js     # Zustand store
        │
        ├── components/
        │   ├── layout/              # MainLayout, Sidebar, Topbar, RightPanel
        │   ├── chat/                # ChatInterface, MessageList
        │   ├── intro/IntroPanel.jsx # Landing greeting + sample data
        │   ├── status/ServerStatusBadge.jsx
        │   ├── workflow/WorkflowProgress.jsx
        │   ├── Upload/FileUploader.jsx
        │   ├── Renderers/           # Table, Markdown, Plotly renderers
        │   ├── data_view/           # Data explorer
        │   ├── Charts/              # Chart components
        │   └── Feedback/ReviewModal.jsx
        │
        ├── pages/ManualPlotPage.jsx
        ├── hooks/
        └── assets/


TECHNOLOGY STACK
================================================================================

BACKEND
-------
- FastAPI 0.115.0
- Uvicorn 0.30.6
- Python 3.11
- Pydantic 2.9.2 / pydantic-settings 2.5.2
- SQLAlchemy 2.0.36 (async) + asyncpg 0.30.0  - Supabase driver
- httpx, tenacity (retry logic)

AI / SANDBOX
------------
- OpenAI-compatible client (OpenRouter): deepseek/deepseek-v4-flash
- E2B Code Interpreter 1.0.5  - secure Python sandbox

DATA
----
- Pandas 2.2.3
- Openpyxl 3.1.5
- PyArrow 17.0.0

FRONTEND
--------
- React 19.2.5
- Vite 8.0.10
- Tailwind CSS 4.2.4
- Zustand 5.0.13
- Axios 1.16.0
- Recharts 3.8.1
- React-Markdown 10.1.0
- Lucide React 1.11.0

DEPLOYMENT
----------
- Backend: Render free-tier web service (Python)
- Frontend: Vercel free-tier static site
- Database: Supabase free-tier PostgreSQL


ENVIRONMENT SETUP (LOCAL)
================================================================================

REQUIREMENTS
------------
- Python 3.11+
- Node.js 18+ and npm
- API Keys: OpenRouter, E2B, Supabase (DATABASE_URL)
- Optional: a sample CSV you want to drop in (default: sample_timeseries.csv)

BACKEND SETUP
-------------
1. cd back_end
2. python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS / Linux:
   source venv/bin/activate
3. pip install -r requirements.txt
4. Create back_end/.env with:
       OPENROUTER_API_KEY=your_openrouter_key
       E2B_API_KEY=your_e2b_key
       DATABASE_URL=postgresql://postgres:Thinh%402802002@db.<ref>.supabase.co:5432/postgres
       BACKEND_SECRET_TOKEN=any-long-random-string
       TEMP_DATA_DIR=temp_data
       LOG_LEVEL=INFO
5. python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

   - Swagger UI: http://localhost:8000/docs
   - Public landing endpoints:
       GET /api/intro
       GET /api/status
       GET /api/sample-data/tell-me
       GET /health

FRONTEND SETUP
--------------
1. cd frontend
2. npm install
3. Create frontend/.env with:
       VITE_API_BASE_URL=http://localhost:8000
       VITE_BACKEND_SECRET_TOKEN=same-as-BACKEND_SECRET_TOKEN
4. npm run dev   # http://localhost:5173


DEPLOYMENT
================================================================================

BACKEND ON RENDER (one-click Blueprint)
----------------------------------------
1. Commit and push the back_end/render.yaml file to GitHub.
2. In Render: New -> Blueprint -> pick the repo.
3. Render reads render.yaml and creates the web service with the
   correct build/start commands, root directory, health check path,
   and environment variable keys.
4. Fill in the values:
       DATABASE_URL       = your Supabase connection string
                           (URL-encode "@" in the password as "%40")
       OPENROUTER_API_KEY = your OpenRouter key
       E2B_API_KEY        = your E2B key
       BACKEND_SECRET_TOKEN = click "Generate" or set a known value
5. Health Check Path: /health
6. After the first deploy, copy the live URL
   (e.g. https://steam-game-data-analyst.onrender.com).

FRONTEND ON VERCEL
------------------
1. In the Vercel project settings, add environment variables:
       VITE_API_BASE_URL          = https://<your-render-service>.onrender.com
       VITE_BACKEND_SECRET_TOKEN  = same value as BACKEND_SECRET_TOKEN
2. Redeploy so Vite picks the new values at build time.
3. The axios client automatically attaches X-API-Key to every
   protected request and skips it for the public landing endpoints
   (/api/intro, /api/status, /api/sample-data/*, /health).

FREE-TIER NOTES
---------------
- Render spins down the service after 15 minutes of inactivity.
  The first request after that takes 30-60 seconds. The frontend
  ServerStatusBadge explains this to the user.
- E2B and Supabase free tiers impose their own limits (compute time
  and database size / egress).
- The startup hook retries the Supabase ping up to 4 times with a
  2-second delay so Render's slow outbound network does not produce
  noisy "Network is unreachable" warnings.


API ENDPOINTS
================================================================================

PUBLIC (no API key)
-------------------
GET  /api/intro
  Returns the landing greeting plus a description of the sample data
  and live database row counts.

GET  /api/status
  Lightweight endpoint for the connection badge. Reports uptime,
  database reachability, and the free-tier warm-up note.

GET  /api/sample-data/tell-me
  Returns a pre-built query string for the "Tell me about this data"
  button on the frontend.

GET  /health
  Health probe used by Render. Reports uptime and database status.

PROTECTED (X-API-Key required)
------------------------------
POST /upload
  Upload a CSV/Excel file (max 100 MB). Returns the AI overview and
  the extracted DataContext.

POST /chat?query=...&include_events=true
  Run the structured AI workflow. Returns the AI response, the last
  executed code, generated artifacts, and (optionally) the list of
  workflow events for the live progress panel.

GET  /tables/{name}
  Get a previously uploaded file as JSON (columns + rows).

GET  /files
  List generated files (CSV / HTML / PNG) in the output directory.

GET  /files/{filename}
  Download or view a generated file. HTML files are served inline so
  Plotly charts render in the browser.

POST /reviews
  Submit a user review (name, rating, message).


WORKFLOW & COMMUNICATION PROTOCOL
================================================================================

The AI and the backend communicate in a strict loop:

1. The frontend sends the user query + selected tables.
2. The system injects the data context and the database summary
   into a structured system prompt.
3. The LLM responds with three lines:

       Response to user: <text> | None
       Request system:   None | E2B_EXE | QUERY_DB | <tool name>
       Code:             <python code> | <json query> | None

4. If Request system is E2B_EXE -> the backend runs the code in
   E2B, downloads new files, and feeds the result back to the LLM.
5. If Request system is QUERY_DB -> the backend runs a safe
   read-only SQLAlchemy query against Supabase and feeds the row
   summary back to the LLM.
6. The loop continues until the LLM returns a non-empty
   "Response to user".

Each iteration is also emitted as a workflow event so the UI can
render a per-step progress panel. A final "done" event marks the
end of the workflow.


SECURITY
================================================================================

AUTHENTICATION
- X-API-Key header required for all /upload, /chat, /files,
  /tables and /reviews endpoints.
- The same secret is shared between back_end/.env
  (BACKEND_SECRET_TOKEN) and frontend/.env
  (VITE_BACKEND_SECRET_TOKEN).
- /api/intro, /api/status, /api/sample-data/* and /health are
  intentionally public so the landing page can render before any
  user interaction.

DATA PROTECTION
- Database: read-only via an allow-list of tables (games, users,
  reviews) and columns; aggregations only.
- File upload: 100 MB max, extension allow-list, sandboxed E2B
  execution.
- Secrets: never committed to the repo. .env files are listed in
  .gitignore at the repo root and inside back_end/.


TROUBLESHOOTING
================================================================================

BACKEND WON'T START
- Check Python 3.11+ is installed.
- Verify all dependencies: pip install -r requirements.txt
- Make sure back_end/.env exists and contains DATABASE_URL.
- Verify port 8000 is free.

FRONTEND WON'T START
- Check Node.js 18+ is installed.
- Clear npm cache: npm cache clean --force
- Reinstall: rm -rf node_modules && npm install
- Verify frontend/.env has VITE_API_BASE_URL and
  VITE_BACKEND_SECRET_TOKEN.

LONG WARM-UP ON RENDER
- The first request after a 15-minute idle period takes 30-60 s
  while the free-tier service spins up.
- The frontend ServerStatusBadge shows "Connecting..." during  this period. The /api/status endpoint is polled every 15-60 s and
  the badge updates to Connected once Supabase responds.

DATABASE CONNECTION FAILS
- Verify DATABASE_URL is correct and URL-encoded (especially "@" -> "%40").
- The startup hook now retries up to 4 times with a 2 s delay to
  ride out Render's slow first outbound connection.
- You can run "python back_end/db_query_smoke.py" locally to confirm
  the credentials work before deploying.

WRONG API KEY / 401 FROM BACKEND
- BACKEND_SECRET_TOKEN in back_end/.env must match
  VITE_BACKEND_SECRET_TOKEN in frontend/.env (and in Vercel settings).
- After updating either side, redeploy so the new value is picked up.


DEVELOPMENT TIPS
================================================================================

LOGGING
- Set LOG_LEVEL=DEBUG in back_end/.env for verbose output.
- Frontend console logs are visible in the browser DevTools.

ADDING NEW TOOLS
- Backend services: add a function in app/services/ and wire it
  into structured_workflow.py (look for the existing E2B_EXE and
  QUERY_DB handlers).
- Frontend: the new panel goes under src/components/ and the
  axios call goes in src/services/api.js. The store update lives
  in src/store/useAppStore.js.

TESTING LOCALLY
- "python back_end/smoke_test.py" exercises the URL parser, ORM
  models, schema description, and query validation without
  hitting the network.
- "python back_end/db_query_smoke.py" runs live SQLAlchemy
  queries against the configured Supabase database and writes
  the output to back_end/db_query_output.txt.


VERSION HISTORY
================================================================================

Version 2.3.0 (Current)
- Removed Upstash Redis dependency. System connects to Supabase only.
- Added SQLAlchemy async models for games, users, reviews.
- Added a read-only database tool (QUERY_DB) for the LLM.
- Added live workflow progress events in /chat responses.
- Added /api/intro, /api/status, /api/sample-data/tell-me endpoints.
- Added IntroPanel, ServerStatusBadge, WorkflowProgress components.
- Pre-loaded sample_timeseries.csv + db.* virtual views at startup.
- Added render.yaml for one-click Render Blueprint deploy.
- Added retry loop on Supabase ping to suppress cold-start warnings.
- All user-facing text now in English without emoji or special chars.


================================================================================
                              END OF README
================================================================================
