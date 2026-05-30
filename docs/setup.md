# InsightPilot Setup

## Frontend

Requirements:

- Node.js 20.9+
- npm

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on:

```text
http://localhost:3000
```

Optional local environment file:

```bash
cp .env.example .env.local
```

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

The backend runs on:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

Optional local environment file:

```bash
copy .env.example .env
```

Optional PDF export support:

```bash
cd backend
python -m pip install -e ".[pdf]"
```

PDF export tries WeasyPrint first so the PDF can mirror the standalone HTML report, including chart exhibits. If WeasyPrint or its native rendering dependencies are unavailable, InsightPilot uses a built-in fallback PDF renderer that still returns a downloadable report with report sections, chart exhibit summaries, and the evidence appendix.

Optional AI narrative polishing:

```bash
ENABLE_AI_NARRATIVE=false
AI_NARRATIVE_API_KEY=
AI_NARRATIVE_BASE_URL=https://api.openai.com/v1/chat/completions
AI_NARRATIVE_MODEL=gpt-4o-mini
```

Keep `ENABLE_AI_NARRATIVE=false` for the default deterministic memo generator. If enabled with a provider key, the backend sends only structured report facts to the AI provider, requires JSON output, validates the rewrite, logs the result, and falls back to the deterministic report on any failure.

## Backend Tests

```bash
cd backend
pytest
```

## Notes

- Frontend upload, preview, profile, chart gallery, insight board, report preview, and HTML export routes are wired to real data.
- PDF export is implemented and returns a downloadable PDF. Installing the optional PDF dependency improves rendering fidelity.
- Backend upload, profiling, chart recommendation, deterministic insight, and executive memo endpoints are implemented.
- The sample CSV is synthetic local development data, not a source of product claims.
