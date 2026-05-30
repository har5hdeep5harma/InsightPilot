# InsightPilot Frontend Design System

Last updated: 2026-05-18

## Direction

InsightPilot uses a report-first studio design language. The interface should feel calm, precise, and premium, with executive memo readability as the center of gravity. Charts and metrics support evidence; they do not define the product.

## Theme

The MVP theme is defined in:

- `frontend/app/globals.css`
- `frontend/tailwind.config.ts`

Core choices:

- Near-white background with exact borders and subtle surfaces.
- Graphite text for authority and readability.
- Restrained blue accent for focus and actionable state.
- Small radius, soft shadows, and no decorative gradients.
- Typography scale for display, heading, body, body-small, and caption text.

Current frontend runtime:

- Next.js 16.2.6
- React 18.3
- Tailwind CSS 3.4
- Node.js 20.9+ required by the current Next.js line

## Components

Implemented reusable components:

- `AppShell`
- `SidebarNavigation`
- `TopCommandBar`
- `PageHeader`
- `Panel`
- `MetricStrip`
- `SectionLabel`
- `EmptyState`
- `LoadingState`
- `ErrorState`
- `StatusBadge`
- `InsightSeverityBadge`
- `EvidenceBadge`
- `EvidenceDrawer` pattern inside `InsightBoardView`
- `ChartContainer`
- `ChartRenderer`
- `ReportPageContainer`

## Routes

- `/`: premium SaaS landing page with hero, product preview, workflow, features, report preview, audience, pricing preview, and final CTA.
- `/studio`: working Upload Studio with drag-and-drop upload, sample CSV upload, parser progress, backend preview, and next action into Dataset Profile.
- `/studio/datasets/{dataset_id}/profile`: Dataset Profile continuation route backed by the profiling API.
- `/studio/datasets/{dataset_id}/charts`: Chart Gallery route backed by the chart recommendation API.
- `/studio/datasets/{dataset_id}/insights`: Insight Board route backed by the deterministic insight API, grouped into analyst briefing sections with a right-side evidence drawer.
- `/studio/datasets/{dataset_id}/report`: Report Preview route backed by the deterministic report API with backend HTML export.

## Interaction Rules

- Do not add buttons without working behavior.
- Do not render charts unless real backend `chart_data` is present.
- Use empty states when data is not loaded yet.
- Keep motion subtle and tied to state changes.
- Keep chart palettes muted and labels clear.
- Keep report pages quieter than workspace pages.

## Current Limitations

- PDF export UI is implemented on the report preview. The backend returns a downloadable PDF with WeasyPrint when available and a built-in fallback renderer otherwise.
