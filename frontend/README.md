# Frontend - Steam Game Data Analyst

React + Vite single-page app that talks to the FastAPI backend on Render.

## What this app does

- Shows a static greeting plus a live description of the sample data
  (a local CSV and three read-only views over the connected
  Supabase Steam database).
- Polls `/api/status` every 15-60 s and renders the result in a
  server-status badge in the top bar, including the free-tier
  warm-up warning.
- Lets the user chat with the LLM. While a request is in flight the
  bottom of the chat area shows a live workflow progress panel
  (Calling AI, Querying database, Running code, ...).
- Shows generated charts in a resizable right panel.

## Tech stack

- React 19
- Vite 8
- Tailwind CSS 4
- Zustand 5 (state)
- Axios 1 (HTTP)
- Lucide React (icons)
- Recharts (manual chart builder)

## Project structure (key files)

```
src/
  App.jsx                          -> renders <MainLayout />
  main.jsx                         -> React entry
  api/axiosClient.js               -> HTTP client, injects X-API-Key
  services/api.js                  -> chat, intro, status, upload, files
  store/useAppStore.js             -> Zustand store (messages, files,
                                     workflow steps, intro, status)

  components/
    layout/   MainLayout, Sidebar, Topbar, RightPanel
    chat/     ChatInterface, MessageList
    intro/    IntroPanel           -> static greeting + sample data
    status/   ServerStatusBadge    -> live top-bar connection badge
    workflow/ WorkflowProgress     -> live per-step workflow panel
    Upload/   FileUploader         -> optional CSV upload
    Renderers/                     -> Markdown, table, Plotly renderers
    data_view/ Charts/ Feedback/
```

## Environment variables

Create `frontend/.env` (this file is gitignored):

```
VITE_API_BASE_URL=https://<your-render-service>.onrender.com
VITE_BACKEND_SECRET_TOKEN=<same value as BACKEND_SECRET_TOKEN in the backend>
```

The axios client automatically attaches `X-API-Key` to every protected
call and skips the header for the public landing endpoints
(`/api/intro`, `/api/status`, `/api/sample-data/*`, `/health`).

## Local development

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Production build

```bash
npm run build   # outputs to dist/
```

The build is served by Vercel from the `dist/` folder.

## Connecting to the backend

1. Start the backend (`uvicorn app.main:app --host 0.0.0.0 --port 8000`).
2. Set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env`.
3. Set `VITE_BACKEND_SECRET_TOKEN` to the same value as
   `BACKEND_SECRET_TOKEN` in `back_end/.env`.
4. `npm run dev` and open the printed URL.

## Where to look in the code

- **Adding a new API call**: `src/services/api.js`.
- **Adding a new landing/status panel**: see `components/intro/`,
  `components/status/`, `components/workflow/`.
- **Wiring a new workflow event**: `src/store/useAppStore.js`
  (`workflowSteps` state).
- **Showing the new event in the progress panel**:
  `components/workflow/WorkflowProgress.jsx` (STAGE_META map).
