# InsightPilot Frontend

Next.js application for the InsightPilot analysis studio.

## Current Surface

The frontend currently includes the premium design system foundation:

- premium landing page at `/`
- working Upload Studio at `/studio`
- Dataset Profile continuation route at `/studio/datasets/{dataset_id}/profile`
- Chart Gallery route at `/studio/datasets/{dataset_id}/charts`
- Insight Board route with evidence drawer at `/studio/datasets/{dataset_id}/insights`
- Report Preview route with HTML export at `/studio/datasets/{dataset_id}/report`
- studio shell with sidebar navigation and top command bar
- report-first page header and layout primitives
- panel, metric strip, state, badge, chart container, and report page components
- restrained Tailwind theme tokens for typography, surfaces, borders, radius, and shadows

The upload, preview, profile, chart gallery, insight board, report preview, and HTML export flows are connected to real backend data. PDF export UI is still pending.

## Local Development

Requirements:

- Node.js 20.9+
- npm

```bash
npm install
npm run dev
```

Default URL:

```text
http://localhost:3000
```

Set `NEXT_PUBLIC_API_BASE_URL` in `.env.local` if the FastAPI backend runs somewhere other than `http://localhost:8000`.
