# InsightPilot

**Turn spreadsheets into executive-grade analysis reports.**

InsightPilot is a premium AI-assisted data analysis studio that converts CSV/XLSX files into profiler output, recommended analytical exhibits, evidence-backed insights, and a polished decision memo.

It is built to answer a practical business problem: many people have spreadsheets, but few have the time or analytical fluency to turn raw rows into a clear, defensible executive report.

## Problem Statement

Most spreadsheet analysis tools stop too early.

Dashboards can show charts, but they often do not explain what matters, why it matters, whether the data is trustworthy, or what action should be considered next. Chatbots can summarize data, but they can also invent unsupported claims if the analytical foundation is weak.

InsightPilot is designed around a stricter workflow:

```text
Raw spreadsheet -> profiling -> chart recommendations -> deterministic insights -> evidence appendix -> executive memo -> export
```

The product prioritizes reliability over theatrical AI output. Analytics are deterministic first. AI, when enabled, is only allowed to polish already-computed report prose.

## Product Demo Flow

1. Open the landing page and enter the Upload Studio.
2. Upload a CSV/XLSX file or choose the built-in SaaS growth sample dataset.
3. Review the parsed dataset preview.
4. Open Dataset Profile to inspect detected roles, missing values, duplicates, warnings, and quality score.
5. Open Chart Gallery to review data-backed chart recommendations.
6. Open Insight Board to inspect evidence-backed findings and their calculations.
7. Generate the Executive Report.
8. Export the report as standalone HTML.
9. Optionally export PDF if local PDF dependencies are installed.

Local routes:

- `/` landing page
- `/studio` upload studio
- `/studio/datasets/{dataset_id}/profile` dataset profile
- `/studio/datasets/{dataset_id}/charts` chart gallery
- `/studio/datasets/{dataset_id}/insights` insight board
- `/studio/datasets/{dataset_id}/report` report preview

## Key Features

- CSV and XLSX upload
- Data preview
- Column profiling
- Column role detection
- Dataset health summary
- Missing value detection
- Duplicate row detection
- Outlier detection
- Summary statistics
- Correlation analysis
- Deterministic chart recommendations
- Evidence-backed insight generation
- Insight evidence drawer in the frontend
- Executive memo generation
- Standalone HTML export
- PDF export with a built-in fallback renderer
- Optional AI narrative polishing with validation
- Realistic SaaS sample dataset
- Evaluation framework for insight reliability

## Why This Is Not Just Another Dashboard

InsightPilot is report-first, not dashboard-first.

Traditional dashboards emphasize visual monitoring. InsightPilot emphasizes analytical interpretation: it profiles the dataset, decides which exhibits are useful, explains evidence, and produces a memo that can be reviewed by a decision-maker.

The UI is intentionally restrained. Charts are treated as exhibits that support findings, not decorative tiles. Every insight has a calculation trail. The report includes an evidence appendix so claims can be traced back to computed values.

## Why InsightPilot Is Reliable

InsightPilot is designed to avoid unsupported analysis.

- **Deterministic analytics first:** profiling, chart recommendations, insights, and report facts are computed before any AI layer is considered.
- **LLM optional:** the product works fully without an API key. AI narrative polishing is disabled by default.
- **Evidence-linked insights:** every generated insight includes structured evidence with calculations, values, columns, row counts where relevant, and explanations.
- **Tested sample datasets:** the SaaS sample intentionally includes known trends, missingness, duplicates, outliers, correlations, and segment differences.
- **No unsupported claims:** the AI polishing layer receives only structured deterministic report facts, must return JSON, and is rejected if it introduces unsupported numeric values.

## Architecture Overview

InsightPilot is a local monorepo:

```text
insightpilot/
  frontend/
  backend/
  sample-data/
  docs/
```

Frontend responsibilities:

- Upload studio
- Dataset preview
- Dataset profile screen
- Chart gallery
- Insight board
- Evidence drawer
- Report preview
- Export actions
- Premium product shell and design system

Backend responsibilities:

- File validation and parsing
- Local artifact persistence
- SQLite metadata persistence
- Dataset profiling
- Chart recommendation
- Deterministic insight generation
- Executive report generation
- HTML export
- PDF export
- Optional AI narrative polishing
- Evaluation runner

The MVP is intentionally not split into microservices. It is structured so one engineer can run and understand it locally, while still leaving room for authentication, workspaces, billing, and external data connectors later.

## Tech Stack

Frontend:

- Next.js 16
- TypeScript
- Tailwind CSS
- shadcn/ui-style primitives
- Framer Motion
- Recharts
- Lucide icons

Backend:

- Python
- FastAPI
- pandas
- Pydantic
- SQLAlchemy
- SQLite
- pytest
- Ruff

Exports and optional AI:

- Standalone HTML export with no external styling dependency
- WeasyPrint PDF generation with built-in fallback
- Optional OpenAI-compatible narrative provider

## Data Analysis Pipeline

The backend pipeline is deterministic:

1. Read uploaded CSV/XLSX.
2. Validate file type, size, headers, parseability, and non-empty rows.
3. Normalize internal column names while preserving original names.
4. Persist upload metadata and parsed dataset artifact.
5. Infer column schema and types.
6. Detect column roles.
7. Compute missingness and uniqueness.
8. Detect duplicate rows.
9. Compute numeric statistics.
10. Detect outliers.
11. Compute correlations.
12. Recommend charts.
13. Generate evidence-backed insight objects.
14. Generate deterministic report sections.
15. Export report.

Supported inferred types:

- numeric
- categorical
- datetime
- boolean
- text
- unknown

Supported roles:

- metric
- dimension
- datetime
- id
- text
- ignored

## Insight Generation Methodology

The insight engine does not use an LLM to discover findings.

Current deterministic insight families:

- Dataset quality insights
- Missing data risk insights
- Trend insights
- Top category insights
- Concentration insights
- Outlier insights
- Correlation insights
- Distribution insights
- Segment difference insights

Insights are filtered for evidence strength. The system prefers a smaller number of useful findings over a large set of weak observations.

## Evidence-Backed Insight System

Each insight includes:

- title
- summary
- insight type
- severity
- confidence
- evidence object
- recommendation
- related columns
- optional related chart

Evidence objects include:

- calculation performed
- relevant columns
- metric name
- computed value
- comparison value
- row counts where relevant
- explanation

This is the core product distinction: the generated memo is not a freeform AI answer. It is assembled from computed evidence.

## Report Generation System

The executive memo generator converts deterministic outputs into a structured report:

- Title
- Dataset overview
- Executive summary
- Key findings
- Risks
- Opportunities
- Recommended actions
- Data quality notes
- Chart references
- Evidence appendix

By default, report prose is generated from deterministic templates.

Optional AI narrative polishing can be enabled with:

```bash
ENABLE_AI_NARRATIVE=true
AI_NARRATIVE_API_KEY=...
AI_NARRATIVE_BASE_URL=https://api.openai.com/v1/chat/completions
AI_NARRATIVE_MODEL=gpt-4o-mini
```

The AI receives only structured report facts and is instructed:

```text
You are rewriting an analytical report using only the provided facts. Do not introduce new claims, numbers, causes, or recommendations. Preserve uncertainty. Keep the tone precise, executive, and concise.
```

If validation fails, InsightPilot falls back to the deterministic report.

## Screenshots

Screenshots are intentionally not faked in this repository.

Recommended screenshots to capture from the local app:

- Landing page: `/`
- Upload Studio with SaaS sample selected: `/studio`
- Dataset Profile quality summary
- Chart Gallery exhibit view
- Insight Board with evidence drawer open
- Executive Report Preview
- Exported HTML report

Suggested location for committed screenshots:

```text
docs/screenshots/
```

## Local Setup

Requirements:

- Node.js 20.9+
- npm
- Python 3.11+

Install and run the backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Backend health check:

```text
http://localhost:8000/health
```

Install and run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

One-command local launch on Windows:

```powershell
.\run-insightpilot.ps1
```

If your Windows execution policy blocks local scripts:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-insightpilot.ps1
```

First-time setup plus launch:

```powershell
.\run-insightpilot.ps1 -Install
```

Useful options:

```powershell
.\run-insightpilot.ps1 -FrontendPort 3001 -BackendPort 8001
.\run-insightpilot.ps1 -NoBrowser
.\run-insightpilot.ps1 -CheckOnly
```

Optional higher-fidelity PDF export:

```bash
cd backend
python -m pip install -e ".[pdf]"
```

PDF export works without this optional dependency by using InsightPilot's built-in PDF fallback renderer. Installing WeasyPrint improves rendering fidelity because the PDF can mirror the standalone HTML report more closely.

## API Documentation

Core local API routes:

- `GET /health`
- `POST /api/datasets/upload`
- `GET /api/datasets/{dataset_id}`
- `GET /api/datasets/{dataset_id}/preview`
- `GET /api/datasets/{dataset_id}/profile`
- `GET /api/datasets/{dataset_id}/charts`
- `GET /api/datasets/{dataset_id}/insights`
- `POST /api/datasets/{dataset_id}/report`
- `GET /api/reports/{report_id}`
- `GET /api/reports/{report_id}/export/html`
- `GET /api/reports/{report_id}/export/pdf`

Detailed API notes:

- [API contract](docs/api-contract.md)
- [Technical architecture](docs/technical-architecture.md)

## Sample Dataset

The primary demo dataset is:

```text
sample-data/saas_growth_sample.csv
```

It contains 2,400 synthetic SaaS customer records with realistic business patterns:

- revenue growth over time
- paid acquisition expansion
- lower-quality paid cohorts
- churn relationships
- support burden patterns
- enterprise revenue concentration
- regional revenue concentration
- missing values
- duplicate rows
- outliers

Supporting files:

- `sample-data/generate_saas_growth_sample.py`
- `sample-data/saas_growth_sample_description.md`
- `sample-data/saas_growth_expected_insights.md`
- `sample-data/saas_growth_demo_walkthrough.md`

The hidden story encoded in the dataset:

```text
Paid acquisition helped grow revenue, but brought lower-usage customers with more support tickets, higher discounts, weaker NPS, and higher churn.
```

## Evaluation Approach

InsightPilot includes a deterministic evaluation framework:

```bash
cd backend
python evals/run_evals.py
```

The eval runner uses the SaaS sample dataset and the real backend routes. It writes:

```text
backend/evals/eval_results.json
```

Eval coverage:

- column role detection
- missing value detection
- duplicate detection
- outlier detection
- trend detection
- top category insight
- concentration insight
- correlation insight
- report generation
- export generation

Insight quality dimensions:

- correctness
- evidence present
- no unsupported claims
- useful recommendation
- severity appropriate
- confidence reasonable

Latest checked result:

```text
InsightPilot eval score: 1.000
All 10 eval suites passed
```

## Current Limitations

- Local MVP only; no authentication or multi-tenant workspaces yet.
- SQLite is used for local persistence.
- Uploaded datasets are stored as local artifacts.
- PDF export includes a built-in fallback renderer; WeasyPrint is optional for higher-fidelity HTML-to-PDF output.
- AI narrative polishing is optional and only supports OpenAI-compatible chat completion APIs.
- The frontend include/exclude chart state is currently local to the report flow.
- Large file handling is intentionally bounded by local MVP limits.

## Future Roadmap

- Authentication
- Workspaces and saved projects
- Team collaboration
- Stripe billing
- Google Sheets import
- Database connectors
- Scheduled reports
- Report version history
- Export history UI
- Persistent chart selection
- More insight families
- Stronger causal caveat detection
- Richer PDF rendering
- Production object storage
- Deployment-ready observability

## Monetization Potential

InsightPilot can become a focused SaaS product for people who need decision-ready analysis without building a BI stack.

Potential pricing paths:

- Free tier for small CSV/XLSX analysis
- Pro tier for larger datasets and exports
- Team tier for shared workspaces and collaboration
- Consultant tier for branded reports and client-ready exports
- Usage-based add-ons for scheduled reports, AI polishing, and external connectors

The commercial wedge is narrow and practical: turn messy spreadsheet data into a credible memo faster than a manual analyst workflow.

## What This Project Demonstrates Technically

InsightPilot demonstrates:

- Product thinking around a real workflow, not a generic dashboard.
- Full-stack TypeScript/Python implementation.
- Deterministic data analysis with pandas.
- FastAPI service design with typed models.
- SQLite persistence and clean repository boundaries.
- Robust upload parsing and validation.
- Column profiling and role inference.
- Deterministic insight generation.
- Evidence-first report generation.
- Optional AI integration with guardrails.
- Premium frontend product design.
- Recharts visualization from real backend data.
- Export generation.
- Evaluation-driven engineering.
- Clear documentation and local developer experience.

## Documentation

- [Project context](insightpilot.md)
- [Technical architecture](docs/technical-architecture.md)
- [API contract](docs/api-contract.md)
- [Analytics rules](docs/analytics-rules.md)
- [Frontend design system](docs/design-system.md)
- [Setup guide](docs/setup.md)
- [Evaluation framework](backend/evals/README.md)

## Product Rule

InsightPilot must not fake insights, charts, or exports. Every insight must be backed by computed evidence from the uploaded or sample dataset.
