================================================================================
                       STEAM GAME DATA ANALYST - README
================================================================================

PROJECT OVERVIEW
================================================================================
Steam Game Data Analyst is a full-stack web application that combines an LLM,
three bundled CSV samples (a daily time-series, Steam game metadata, and user
reviews), an E2B Python sandbox, and interactive Plotly charts.

Users can ask natural-language questions about the bundled data without
uploading anything, and can also drop in their own CSV/Excel files for one-off
analysis. The AI agent can describe the data, run read-only QUERY_CSV queries
against the bundled samples, and execute Python visualisation code in a
sandbox.

The system uses a strict AI-System communication protocol: the LLM replies with
`Response to user / Request system / Code`, and the backend services follow the
request until the LLM is ready to answer. Every step is emitted as a workflow
event so the UI can show a live progress panel.


KEY FEATURES
================================================================================
1. PRE-LOADED SAMPLE DATA
   - Three small CSVs are registered on startup so there is always
     something to ask about:
       * sample_timeseries.csv - daily revenue series (2024-2025)
       * metadata.csv          - 30 Steam games (name, release date, ...)
       * reviews.csv           - 25 user reviews (no review_text column)
   - One-click "Tell me about this data" button on every sample card.

2. NATURAL LANGUAGE CHAT INTERFACE
   - Plain-English chat with the AI about any of the registered tables.
   - Live workflow panel that shows what the backend is currently doing
     (Calling AI, Querying CSV, Running code, Finalising).
   - Per-step retry and error reporting.

3. CSV QUERY TOOL (LLM can read the bundled CSVs)
   - The model emits `Request system: QUERY_CSV` with a JSON payload
     describing the table, columns, filters, ordering, and limit.
   - The backend runs a safe, read-only pandas query against the bundled
     CSV and feeds the result back to the LLM as additional context.

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

  +---------------------+    X-API-Key    +----------------------------+
  |  Vercel (Free)      | --------------> |  Render (Free)             |
  |  React + Vite SPA   |                 |  FastAPI app.main:app      |
  |                     |                 |                            |
  |  - IntroPanel       |                 |  Routers:                  |
  |  - ChatInterface    |                 |   /api/intro (public)      |
  |  - ServerStatus     |                 |   /api/status (public)     |
  |  - WorkflowProg.    |                 |   /api/sample-data/* (pub) |
  |  - Sidebar/Upload   |                 |   /health (public)         |
  |                     |                 |   /upload, /chat, /files,  |
  +---------------------+                 |   /tables, /reviews       |
                                          |                            |
                                          |  Services:                 |
                                          |   LLMService (OpenRouter) |
                                          |   DBService (CSV queries) |
                                          |   E2BService (sandbox)     |
                                          |   SampleDataService        |
                                          |   StructuredWorkflow       |
                                          +------------+---------------+
                                                       |
                                                       v
                                          +----------------------------+
                                          |  Bundled CSV samples       |
                                          |  (in back_end/temp_data/)  |
                                          |                            |
                                          |  sample_timeseries.csv     |
                                          |  metadata.csv              |
                                          |  reviews.csv               |
                                          +----------------------------+


PROJECT STRUCTURE
================================================================================

ROOT DIRECTORY
|
|-- README.txt                       # This file
|-- .gitignore                       # Repo-level ignore rules
|-- metadata.csv                     # Bundled sample (30 Steam games)
|-- reviews.csv                      # Bundled sample (25 reviews)
|
|-- back_end/                        # FastAPI backend
|   |-- requirements.txt             # Python dependencies
|   |-- render.yaml                  # One-click Render Blueprint
|   |-- SCHEMA_DOCUMENTATION.md      # Original DB schema reference
|   |-- smoke_test.py                # Local smoke test (CSV-only mode)
|   |-- sample_timeseries.csv        # Bundled CSV sample
|   |-- app/
|   |   |-- main.py                  # FastAPI entry point
|   |   |
|   |   |-- api/routers/
|   |   |   |-- info.py              # /api/intro, /api/status (public)
|   |   |   |-- chat.py              # /chat (the workflow)
|   |   |   |-- upload.py            # /upload (CSV/Excel ingest)
|   |   |   |-- manual_plot.py       # /tables/{id} (manual charts)
|   |   |   |-- reviews.py           # /reviews
|   |   |   `-- download.py          # /files, /files/{name}
|   |   |
|   |   |-- core/
|   |   |   |-- config.py            # Pydantic settings
|   |   |   `-- security.py          # X-API-Key auth
|   |   |
|   |   |-- services/
|   |   |   |-- llm_service.py           # OpenRouter client
|   |   |   |-- data_service.py          # DataContext extraction
|   |   |   |-- e2b_service.py           # (legacy agentic workflow)
|   |   |   |-- db_service.py            # CSV query tool (read-only)
|   |   |   |-- session_service.py       # In-memory session state
|   |   |   |-- sample_data_service.py   # Registers sample tables
|   |   |   `-- structured_workflow.py   # AI <-> System protocol loop
|   |   |
|   |   `-- utils/
|   |       `-- response_formatter.py
|   |
|   `-- temp_data/                   # Working dir for generated files
|
`-- frontend/                        # React + Vite frontend
    |-- package.json
    |-- vite.config.js
    |-- tailwind.config.js
    |-- eslint.config.js
    |-- index.html
    |-- .env                         # VITE_API_BASE_URL + secret (gitignored)
    |
    |-- public/
    `-- src/
        |-- main.jsx
        |-- App.jsx
        |
        |-- api/axiosClient.js       # Axios + X-API-Key injection
        |-- services/api.js          # API client (chat, intro, status)
        |-- store/useAppStore.js     # Zustand store
        |
        |-- components/
        |   |-- layout/              # MainLayout, Sidebar, Topbar, RightPanel
        |   |-- chat/                # ChatInterface, MessageList
        |   |-- intro/IntroPanel.jsx # Landing greeting + sample data
        |   |-- status/ServerStatusBadge.jsx
        |   |-- workflow/WorkflowProgress.jsx
        |   |-- Upload/FileUploader.jsx
        |   |-- Renderers/           # Table, Markdown, Plotly renderers
        |   |-- data_view/           # Data explorer
        |   |-- Charts/              # Chart components
        |   `-- Feedback/ReviewModal.jsx
        |
        |-- pages/ManualPlotPage.jsx
        |-- hooks/
        `-- assets/


TECHNOLOGY STACK
================================================================================

BACKEND
-------
- FastAPI 0.115.0
- Uvicorn 0.30.6
- Python 3.11
- Pydantic 2.9.2 / pydantic-settings 2.5.2
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
- Data: three bundled CSV files (no external database)


ENVIRONMENT SETUP (LOCAL)
================================================================================

REQUIREMENTS
------------
- Python 3.11+
- Node.js 18+ and npm
- API Keys: OpenRouter, E2B

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
- E2B free tier imposes its own limits (compute time per request).
- All data lives in three small CSV files bundled with the backend,
  so no external database connection is needed.


API ENDPOINTS
================================================================================

PUBLIC (no API key)
-------------------
GET  /api/intro
  Returns the landing greeting plus a description of every bundled
  CSV sample.

GET  /api/status
  Lightweight endpoint for the connection badge. Reports uptime
  and the free-tier warm-up note.

GET  /api/sample-data/tell-me
  Returns a pre-built query string for the "Tell me about this data"
  button on the frontend.

GET  /health
  Health probe used by Render. Reports uptime and the list of
  sample files in temp_data/.

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
2. The system injects the data context into a structured system prompt.
3. The LLM responds with three lines:

       Response to user: <text> | None
       Request system:   None | E2B_EXE | QUERY_CSV | <tool name>
       Code:             <python code> | <json query> | None

4. If Request system is E2B_EXE -> the backend runs the code in
   E2B, downloads new files, and feeds the result back to the LLM.
5. If Request system is QUERY_CSV -> the backend runs a safe
   read-only pandas query against the bundled CSV and feeds the row
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
- CSV queries: read-only via an allow-list of tables (metadata,
  reviews, sample_timeseries) and columns; whitelisted operators.
- File upload: 100 MB max, extension allow-list, sandboxed E2B
  execution.
- Secrets: never committed to the repo. .env files are listed in
  .gitignore at the repo root and inside back_end/.


TROUBLESHOOTING
================================================================================

BACKEND WON'T START
- Check Python 3.11+ is installed.
- Verify all dependencies: pip install -r requirements.txt
- Make sure back_end/.env exists and contains OPENROUTER_API_KEY
  and E2B_API_KEY.
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
- The frontend ServerStatusBadge shows "Connecting..." during this
  period. The /api/status endpoint is polled and the badge updates
  to Connected once the backend responds.

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
  QUERY_CSV handlers).
- Frontend: the new panel goes under src/components/ and the
  axios call goes in src/services/api.js. The store update lives
  in src/store/useAppStore.js.

TESTING LOCALLY
- "python back_end/smoke_test.py" exercises the CSV-only mode:
  describes all bundled tables, runs queries against metadata,
  reviews and sample_timeseries, and validates the intro payload.


VERSION HISTORY
================================================================================

Version 2.4.0 (Current)
- Removed Supabase / asyncpg / SQLAlchemy dependencies entirely.
- All data lives in three bundled CSV files (metadata.csv,
  reviews.csv, sample_timeseries.csv).
- LLM tool replaced QUERY_DB with QUERY_CSV (read-only pandas).
- New /api/intro, /api/status, /api/sample-data/tell-me endpoints.
- New IntroPanel + ServerStatusBadge + WorkflowProgress components.
- Pre-loaded samples are three CSVs in back_end/temp_data/ that the
  backend registers on startup.
- Smoke test now exercises CSV tools (no Supabase).
- All user-facing text in English without emoji or special chars.
- render.yaml Blueprint for one-click Render deploy.

Version 2.3.0
- Removed Upstash Redis dependency. System connected to Supabase only.
- Added SQLAlchemy async models for games, users, reviews.
- Added a read-only database tool (QUERY_DB) for the LLM.
- Added live workflow progress events in /chat responses.


                              END OF README
