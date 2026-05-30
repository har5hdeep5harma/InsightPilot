# InsightPilot Technical Architecture

Last updated: 2026-05-17

## Engineering Goal

Build a reliable local MVP that can later become a SaaS product without pretending to be one on day one. The first version should be simple enough for one engineer plus Codex to build, but structured enough that auth, billing, teams, external data sources, and an AI narrative layer can be added later.

The core architecture is a two-app monorepo:

```text
Next.js web app -> FastAPI backend -> SQLite + local files
```

There are no microservices in the MVP. The backend is the source of truth for analysis, chart specs, evidence, reports, and exports.

## 1. Frontend Architecture

### Framework

- Next.js 16.2.6 App Router for the current local MVP
- TypeScript
- Tailwind CSS
- shadcn/ui
- Framer Motion
- Recharts

### App Structure

```text
frontend/
  app/
    layout.tsx
    page.tsx
    loading.tsx
    error.tsx
    not-found.tsx
    analyses/
      [analysisId]/
        page.tsx
        loading.tsx
        error.tsx
    reports/
      [analysisId]/
        page.tsx
  components/
    ui/
    layout/
      app-shell.tsx
    upload/
      UploadPanel.tsx
      UploadDropzone.tsx
      SampleDatasetButton.tsx
      UploadRequirements.tsx
    profile/
      AnalysisWorkspace.tsx
      DatasetSummary.tsx
      DatasetPreviewTable.tsx
      HealthSummary.tsx
      ColumnProfileTable.tsx
      MissingnessPanel.tsx
      DuplicatePanel.tsx
      CorrelationPanel.tsx
      OutlierPanel.tsx
    charts/
      ChartDeck.tsx
      ChartCard.tsx
      ChartRenderer.tsx
      BarChartView.tsx
      LineChartView.tsx
      ScatterChartView.tsx
      HistogramView.tsx
      HeatmapView.tsx
    insights/
      InsightList.tsx
      InsightCard.tsx
      EvidenceList.tsx
    report/
      ReportPreview.tsx
      ReportSection.tsx
      ExecutiveMemo.tsx
    export/
      ExportToolbar.tsx
  lib/
  types/
  hooks/
```

### Page Routes

`/`

- Main studio entry point.
- Shows upload panel and sample dataset action.
- If recent local analyses are implemented later, they can appear below the primary upload flow.
- No marketing landing page in the MVP.

`/analyses/[analysisId]`

- Main analysis workspace.
- Shows dataset summary, preview, health, profiles, recommended charts, insights, and report preview.
- This is the core product screen.

`/reports/[analysisId]`

- Focused executive report preview.
- Uses the same report JSON as the workspace.
- Provides export actions only when the backend confirms they are available.

### Component Hierarchy

```text
AppShell
  TopBar
  WorkspaceFrame
    UploadPanel
      UploadDropzone
      SampleDatasetButton
      UploadRequirements

AnalysisWorkspace
  DatasetSummary
  HealthSummary
  DatasetPreviewTable
  ColumnProfileTable
  ChartDeck
    ChartCard
      ChartRenderer
        BarChartView | LineChartView | ScatterChartView | HistogramView | HeatmapView
  InsightList
    InsightCard
      EvidenceList
  ReportPreview
    ExecutiveMemo
    ReportSection
    ExportToolbar
```

### State Management Approach

Use the URL and backend persistence as the primary state model.

MVP frontend state:

- Upload form state: local React state.
- Active analysis ID: URL param.
- Server data: custom typed API hooks with fetch and React state.
- Local UI state: component state for active tabs, expanded insight cards, table pagination, and chart focus.

Avoid a global client store in the MVP. It is not needed while there is one active dataset/analysis flow. If cache invalidation, polling, retries, and optimistic updates become complex, add TanStack Query later as a focused server-state layer.

### Upload Flow

1. User drops or selects a CSV/XLSX file.
2. Frontend validates extension and approximate file size before upload.
3. Frontend calls `POST /datasets`.
4. Backend validates, stores the original upload, parses a preview, creates dataset metadata, and returns `dataset_id`.
5. Frontend calls `POST /datasets/{dataset_id}/analyze`.
6. Backend runs the deterministic pipeline synchronously for MVP-sized files.
7. Backend persists the analysis result and returns `analysis_id`.
8. Frontend navigates to `/analyses/{analysis_id}`.
9. Workspace fetches `GET /analyses/{analysis_id}`.

For the sample dataset, the frontend loads the bundled public CSV and sends it through the same `POST /api/datasets/upload` endpoint as a user-selected file. There is no separate fake sample response.

### Chart Rendering Flow

The frontend does not decide which charts are valid. The backend emits `ChartSpec` objects using actual analyzed data.

Flow:

1. Backend detects column roles and useful pairings.
2. Backend computes aggregated or sampled chart data.
3. Backend returns `chart_specs` in analysis response.
4. `ChartDeck` filters unsupported chart types defensively.
5. `ChartRenderer` maps each supported `ChartSpec.type` to a Recharts component.
6. If a chart spec has no data after filtering, the frontend shows a clear unavailable state for that chart instead of rendering an empty visualization.

Chart data should be pre-aggregated by the backend for consistency with evidence and report text.

### Report Rendering Flow

The report is generated from the same deterministic analysis result used by the cards and charts.

Flow:

1. Backend produces `Report` JSON with sections, summary, insight references, chart references, warnings, and methodology notes.
2. Frontend renders the report with `ReportPreview`.
3. HTML export uses the backend report model and a server-side HTML template.
4. PDF export, if available, renders from the same HTML.

The report preview and export must never contain insights that are absent from the persisted analysis.

### Error, Loading, And Empty State Strategy

Loading states:

- Upload progress indicator during file transfer.
- Analysis progress state while deterministic profiling runs.
- Skeleton blocks for workspace sections while `GET /analyses/{analysis_id}` loads.

Empty states:

- No dataset uploaded: show upload/sample dataset actions.
- No valid charts: explain which data shape is needed, based on computed column roles.
- No insights: state that no material patterns crossed deterministic thresholds.
- No correlations: state that at least two numeric columns are required.

Error states:

- File rejected: show exact reason and accepted formats.
- Parse failed: show encoding/sheet/header issue when known.
- Analysis failed: show recoverable message and preserve dataset metadata if upload succeeded.
- Export degraded: keep HTML export available and use the built-in PDF fallback if the higher-fidelity PDF renderer is unavailable.
- API unavailable: show connection error and local dev command hints in README, not in product UI.

All errors should use backend error codes so UI copy can be precise.

## 2. Backend Architecture

### Framework

- Python FastAPI
- Pydantic v2 for request/response schemas
- pandas for MVP analytics
- SQLAlchemy 2 for SQLite persistence
- Jinja2 for HTML report templates
- Optional PDF dependency later, behind a capability check

### Service Structure

```text
backend/
  app/
    main.py
    api/
      health.py
      datasets.py
      analyses.py
      exports.py
    core/
      config.py
      errors.py
    models/
      dataset.py
      profile.py
      chart.py
      insight.py
      report.py
      export.py
    services/
      parsing/
      profiling/
      charts/
      insights/
      reports/
      export/
    db/
      session.py
  tests/
```

### Upload Endpoint

`POST /datasets`

Responsibilities:

- Accept multipart CSV/XLSX upload.
- Enforce file size limit.
- Validate extension and content type.
- Store original file in `data/uploads/{dataset_id}/`.
- Parse enough to validate rows/columns.
- Create dataset metadata record.
- Return dataset metadata and warnings.

The endpoint does not invent a successful dataset if parsing fails. It returns a typed error and does not create a usable dataset record.

### Dataset Parsing Service

Responsibilities:

- Read CSV with encoding fallback.
- Read XLSX first visible sheet for MVP.
- Normalize headers.
- Detect duplicate headers and disambiguate internally.
- Preserve original column names in metadata.
- Reject empty datasets.
- Apply row/column limits.
- Produce parse warnings.

CSV encoding strategy:

1. Try `utf-8-sig`.
2. Try `utf-8`.
3. Try `cp1252`.
4. Try `latin-1`.
5. Fail with `UNSUPPORTED_ENCODING` if parsing still fails.

### Profiling Service

Responsibilities:

- Infer column type and role.
- Compute column-level summary.
- Compute dataset-level health.
- Compute missingness and duplicate rows.
- Compute numeric summary statistics.
- Compute outliers.
- Compute correlations.

The profiling service returns structured data, not prose.

### Chart Recommendation Service

Responsibilities:

- Use column roles and computed distributions.
- Generate only chart specs that have enough valid data.
- Pre-aggregate chart data.
- Add rationale and limitations.
- Limit high-cardinality categories with top N plus optional "Other".

Supported MVP chart types:

- Bar: categorical dimension vs numeric metric.
- Line: datetime dimension vs numeric metric.
- Histogram: numeric distribution.
- Scatter: numeric vs numeric.
- Heatmap: numeric correlation matrix.

### Insight Generation Service

Responsibilities:

- Generate deterministic `Insight` objects from thresholds and evidence.
- Attach one or more `Evidence` objects to every insight.
- Reference related columns and chart specs when applicable.
- Avoid vague or generic findings.
- Return no insight when evidence does not meet thresholds.

Example deterministic insight families:

- High missingness in important columns.
- Duplicate row risk.
- Strong numeric correlation.
- Significant outliers.
- Metric concentration by category.
- Time-based trend when a datetime column and metric exist.
- Category imbalance or long-tail distribution.

### Report Generation Service

Responsibilities:

- Assemble executive report sections from dataset metadata, profile, chart specs, insights, and evidence.
- Include dataset overview, data quality notes, and evidence appendix.
- Reference insight IDs and chart IDs.
- Produce deterministic default memo text.
- Optionally call an LLM rewrite layer only after facts are generated; local MVP does not implement a provider.

Report sections:

- Executive summary
- Dataset overview
- Data quality notes
- Key findings
- Risks
- Opportunities
- Recommended actions
- Charts included
- Appendix with evidence

### Export Service

Responsibilities:

- Create export job records.
- Generate HTML reports from the persisted `Report` model.
- Store export files in `data/exports/{export_id}/`.
- Return export status and download URL.
- Support PDF only when the configured renderer is installed.

HTML export is required. PDF export should return a downloadable PDF. The backend should use the higher-fidelity HTML-to-PDF renderer when available and fall back to a built-in PDF renderer when local native PDF dependencies are unavailable.

### Persistence Layer

SQLite is the local MVP database. SQLAlchemy repositories isolate database operations from services.

Recommended tables:

```text
datasets
  id TEXT PRIMARY KEY
  filename TEXT NOT NULL
  original_file_path TEXT NOT NULL
  file_type TEXT NOT NULL
  file_size_bytes INTEGER NOT NULL
  row_count INTEGER NOT NULL
  column_count INTEGER NOT NULL
  status TEXT NOT NULL
  parse_warnings_json TEXT NOT NULL
  created_at TEXT NOT NULL

analysis_runs
  id TEXT PRIMARY KEY
  dataset_id TEXT NOT NULL
  status TEXT NOT NULL
  health_json TEXT NOT NULL
  statistics_json TEXT NOT NULL
  correlations_json TEXT NOT NULL
  outliers_json TEXT NOT NULL
  warnings_json TEXT NOT NULL
  created_at TEXT NOT NULL
  completed_at TEXT

column_profiles
  id TEXT PRIMARY KEY
  analysis_id TEXT NOT NULL
  dataset_id TEXT NOT NULL
  column_name TEXT NOT NULL
  original_column_name TEXT NOT NULL
  dtype TEXT NOT NULL
  role TEXT NOT NULL
  profile_json TEXT NOT NULL

chart_specs
  id TEXT PRIMARY KEY
  analysis_id TEXT NOT NULL
  type TEXT NOT NULL
  title TEXT NOT NULL
  spec_json TEXT NOT NULL

insights
  id TEXT PRIMARY KEY
  analysis_id TEXT NOT NULL
  severity TEXT NOT NULL
  category TEXT NOT NULL
  title TEXT NOT NULL
  insight_json TEXT NOT NULL

reports
  id TEXT PRIMARY KEY
  analysis_id TEXT NOT NULL
  title TEXT NOT NULL
  report_json TEXT NOT NULL
  created_at TEXT NOT NULL

export_jobs
  id TEXT PRIMARY KEY
  analysis_id TEXT NOT NULL
  report_id TEXT NOT NULL
  format TEXT NOT NULL
  status TEXT NOT NULL
  file_path TEXT
  error_json TEXT
  created_at TEXT NOT NULL
  completed_at TEXT
```

For MVP speed, JSON fields are acceptable because analysis payloads are read as whole report objects. If filtering and multi-user query patterns grow, normalize more fields later.

## 3. Data Analysis Pipeline

The analysis pipeline is deterministic. It should produce the same output for the same input file and version of the code.

### Pipeline Steps

1. Receive file.
2. Validate file size, extension, and readable content.
3. Store original upload.
4. Parse file into a dataframe.
5. Normalize column names while preserving originals.
6. Validate non-empty rows and columns.
7. Infer schema.
8. Detect column types.
9. Detect column roles.
10. Compute dataset-level statistics.
11. Compute missingness.
12. Compute duplicate rows.
13. Compute outliers.
14. Compute correlations.
15. Recommend charts.
16. Generate evidence-backed insight objects.
17. Generate report sections.
18. Persist analysis artifacts.
19. Return analysis ID and full analysis payload.

### Schema Inference

Column dtype categories:

- `numeric`
- `categorical`
- `boolean`
- `datetime`
- `text`
- `unknown`

Inference should use confidence thresholds. For example, a string column becomes `datetime` only if a high percentage of non-empty values parse successfully.

### Role Detection

Column roles:

- `metric`: numeric values useful for aggregation.
- `dimension`: categorical or boolean values useful for grouping.
- `datetime`: time axis.
- `id`: unique or near-unique ID values.
- `text`: long text not useful as a compact dimension.
- `ignored`: mostly missing or insufficient signal.

Heuristics:

- Numeric with many unique values: likely `metric`.
- Numeric with ID-like name or long sequential uniqueness: possible `id`.
- String with low-to-medium cardinality: `dimension`.
- String with very high cardinality: `id` if name-like ID, otherwise `text`.
- Date-like column with parse confidence above threshold: `datetime`.
- Boolean-like values: `dimension`.

### Statistics

Numeric columns:

- count
- missing count and percent
- min
- max
- mean
- median
- standard deviation
- quartiles
- zero count
- negative count

Categorical columns:

- count
- missing count and percent
- unique count
- top values
- cardinality ratio

Datetime columns:

- count
- missing count and percent
- min date
- max date
- inferred granularity where possible

### Missingness

Compute:

- Missing cells by column.
- Missing percent by column.
- Dataset-level missing cell percent.
- Rows with any missing value.
- High-risk columns above threshold.

Suggested thresholds:

- `warning`: missing percent >= 10%
- `critical`: missing percent >= 30%

### Duplicate Rows

Compute:

- Exact duplicate row count.
- Exact duplicate row percent.
- Sample duplicate row indexes for evidence.

Do not delete duplicates automatically. Report them.

### Outliers

MVP method:

- IQR method for numeric columns.
- Lower bound: Q1 - 1.5 * IQR.
- Upper bound: Q3 + 1.5 * IQR.
- Count and percent outliers by numeric column.

Skip outlier detection when a numeric column has too few valid values or zero variance.

### Correlations

MVP method:

- Pearson correlation for numeric metric columns.
- Ignore pairs with insufficient non-null overlap.
- Return strongest positive and negative correlations above threshold.

Suggested threshold:

- `abs(correlation) >= 0.65`

### Chart Recommendations

Rules:

- At least one `datetime` and one `metric`: line chart over time.
- At least one `dimension` and one `metric`: bar chart of metric aggregated by dimension.
- At least one `metric`: histogram.
- At least two `metric` columns: scatter and correlation heatmap.
- High-cardinality dimensions should be top N grouped by aggregate value, not raw categories.

### Insight Generation

Insight rules must be evidence-first:

```text
condition met -> compute evidence -> create insight -> link chart when available
```

Every insight must include:

- title
- narrative
- category
- severity
- evidence array
- related columns
- optional chart reference
- deterministic rule ID

No evidence means no insight.

### Report Sections

Report generation uses the analysis objects:

- Executive summary from top evidence-backed insights.
- Dataset overview from metadata and health.
- Data quality from missingness, duplicates, and parsing warnings.
- Key findings from insight objects.
- Recommended charts from chart specs.
- Methodology from pipeline configuration.

## 4. Data Models

The canonical API models should be represented as Pydantic schemas in the backend and mirrored as TypeScript types in the frontend.

### Dataset

```ts
type DatasetStatus = "uploaded" | "parsed" | "analysis_failed" | "deleted";

type Dataset = {
  id: string;
  filename: string;
  fileType: "csv" | "xlsx";
  fileSizeBytes: number;
  rowCount: number;
  columnCount: number;
  status: DatasetStatus;
  parseWarnings: AnalysisWarning[];
  createdAt: string;
};
```

### ColumnProfile

```ts
type ColumnDType =
  | "numeric"
  | "categorical"
  | "boolean"
  | "datetime"
  | "text"
  | "unknown";

type ColumnRole =
  | "metric"
  | "dimension"
  | "datetime"
  | "id"
  | "text"
  | "ignored";

type ColumnProfile = {
  name: string;
  originalName: string;
  inferredType: ColumnDType;
  role: ColumnRole;
  missingCount: number;
  missingPercentage: number;
  uniqueCount: number;
  uniquePercentage: number;
  sampleValues: unknown[];
  min?: unknown;
  max?: unknown;
  mean?: number;
  median?: number;
  std?: number;
  topValues: Array<{ value: unknown; count: number; percentage: number }>;
  warnings: AnalysisWarning[];
};
```

### DatasetProfile

```ts
type DatasetProfile = {
  datasetId: string;
  rowCount: number;
  columnCount: number;
  duplicateRowCount: number;
  memoryUsage: number;
  columns: ColumnProfile[];
  numericColumns: string[];
  categoricalColumns: string[];
  datetimeColumns: string[];
  idLikeColumns: string[];
  textColumns: string[];
  qualityScore: number;
  warnings: AnalysisWarning[];
};
```

### ChartSpec

```ts
type ChartType =
  | "line"
  | "bar"
  | "horizontal_bar"
  | "histogram"
  | "scatter"
  | "correlation_heatmap"
  | "box_plot"
  | "stacked_bar";

type ChartSpec = {
  id: string;
  datasetId: string;
  chartType: ChartType;
  title: string;
  xColumn?: string;
  yColumn?: string;
  groupBy?: string;
  description: string;
  reasoning: string;
  priority: number;
  chartData: Record<string, unknown>[];
};
```

### Evidence

```ts
type Evidence = {
  type: string;
  column?: string;
  columns: string[];
  metric: string;
  value: unknown;
  comparisonValue?: unknown;
  values: Record<string, unknown>;
  comparisonValues: Record<string, unknown>;
  rowsAffected?: number;
  calculation: string;
  explanation: string;
};
```

### Insight

```ts
type InsightSeverity = "low" | "medium" | "high";
type InsightCategory =
  | "dataset_quality"
  | "trend"
  | "top_category"
  | "correlation"
  | "outlier"
  | "concentration"
  | "distribution"
  | "missing_data_risk"
  | "segment_difference";

type Insight = {
  id: string;
  datasetId: string;
  severity: InsightSeverity;
  insightType: InsightCategory;
  title: string;
  summary: string;
  confidence: number;
  evidence: Evidence;
  relatedColumns: string[];
  relatedChartId?: string;
};
```

### Report

```ts
type Report = {
  reportId: string;
  title: string;
  datasetOverview: string;
  executiveSummary: string;
  keyFindings: string[];
  risks: string[];
  opportunities: string[];
  recommendations: string[];
  evidenceAppendix: Array<{
    insightId: string;
    insightTitle: string;
    insightType: string;
    evidence: Evidence;
  }>;
  chartIds: string[];
};
```

### ExportJob

```ts
type ExportFormat = "html" | "pdf";
type ExportStatus = "queued" | "running" | "completed" | "failed" | "unsupported";

type ExportJob = {
  id: string;
  analysisId: string;
  reportId: string;
  format: ExportFormat;
  status: ExportStatus;
  downloadUrl?: string;
  error?: ApiError;
  createdAt: string;
  completedAt?: string;
};
```

### Shared Warning And Error

```ts
type AnalysisWarning = {
  code: string;
  message: string;
  column?: string;
  details?: Record<string, unknown>;
};

type ApiError = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};
```

## 5. Storage

SQLite stores durable metadata and generated analysis artifacts. The original upload and export files live on disk.

### Local File Layout

```text
data/
  insightpilot.sqlite
  samples/
    sample_retail_sales.csv
  uploads/
    {dataset_id}/
      original.csv
  exports/
    {export_id}/
      report.html
      report.pdf
```

### Stored Data

Store in SQLite:

- Uploaded dataset metadata.
- Parse warnings.
- Column profiles.
- Dataset health.
- Summary statistics.
- Correlations.
- Outlier summaries.
- Chart specs.
- Insights.
- Generated reports.
- Export history.

Do not store every uploaded row in SQLite for the MVP. Keep the original uploaded file on disk and store analysis artifacts in SQLite. If row-level querying becomes necessary later, add a local analytical store or normalized table strategy.

## 6. API Contract

### Error Envelope

All non-2xx responses use:

```json
{
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "Only CSV and XLSX files are supported.",
    "details": {}
  }
}
```

### GET /health

Request body: none

Response:

```json
{
  "status": "ok"
}
```

Error states:

- `500 INTERNAL_ERROR`

### POST /datasets

Request body:

Multipart form data:

- `file`: CSV or XLSX

Response:

```json
{
  "dataset": {
    "id": "ds_123",
    "filename": "sales.csv",
    "fileType": "csv",
    "fileSizeBytes": 120000,
    "rowCount": 1000,
    "columnCount": 12,
    "status": "parsed",
    "parseWarnings": [],
    "createdAt": "2026-05-17T10:00:00Z"
  }
}
```

Error states:

- `400 MISSING_FILE`
- `413 FILE_TOO_LARGE`
- `415 INVALID_FILE_TYPE`
- `422 EMPTY_DATASET`
- `422 PARSE_FAILED`
- `422 DUPLICATE_COLUMNS_UNRESOLVABLE`
- `500 STORAGE_ERROR`

### Sample Dataset

The frontend sample action loads `frontend/public/sample-data/sample_retail_sales.csv` and uploads it through `POST /api/datasets/upload`. The MVP does not expose a separate sample-dataset API route.

Error states:

- Static sample file missing in the frontend: show `SAMPLE_DATASET_UNAVAILABLE`.
- Backend upload/parser failure: show the normal upload endpoint error.

### GET /datasets/{dataset_id}

Request body: none

Response:

```json
{
  "dataset": {}
}
```

Error states:

- `404 DATASET_NOT_FOUND`

### GET /datasets/{dataset_id}/preview

Query params:

- `limit`: default `50`, max `200`
- `offset`: default `0`

Request body: none

Response:

```json
{
  "columns": [
    {
      "name": "revenue",
      "originalName": "Revenue"
    }
  ],
  "rows": [
    {
      "revenue": 1200
    }
  ],
  "limit": 50,
  "offset": 0,
  "totalRows": 1000
}
```

Error states:

- `404 DATASET_NOT_FOUND`
- `422 PREVIEW_UNAVAILABLE`

### POST /datasets/{dataset_id}/analyze

Request body:

```json
{
  "force": false
}
```

Response:

```json
{
  "analysis": {
    "id": "an_123",
    "datasetId": "ds_123",
    "status": "completed",
    "profile": {},
    "chartSpecs": [],
    "insights": [],
    "report": {}
  }
}
```

Error states:

- `404 DATASET_NOT_FOUND`
- `409 ANALYSIS_ALREADY_EXISTS`
- `422 DATASET_NOT_ANALYZABLE`
- `500 ANALYSIS_FAILED`

If `force` is true, the backend may create a new analysis run for the same dataset.

### GET /analyses/{analysis_id}

Request body: none

Response:

```json
{
  "analysis": {
    "id": "an_123",
    "datasetId": "ds_123",
    "status": "completed",
    "dataset": {},
    "profile": {},
    "chartSpecs": [],
    "insights": [],
    "report": {}
  }
}
```

Error states:

- `404 ANALYSIS_NOT_FOUND`

### GET /analyses/{analysis_id}/report

Request body: none

Response:

```json
{
  "report": {}
}
```

Error states:

- `404 ANALYSIS_NOT_FOUND`
- `404 REPORT_NOT_FOUND`

### POST /analyses/{analysis_id}/exports/html

Request body: none

Response:

```json
{
  "exportJob": {
    "id": "ex_123",
    "analysisId": "an_123",
    "reportId": "rp_123",
    "format": "html",
    "status": "completed",
    "downloadUrl": "/exports/ex_123/download",
    "createdAt": "2026-05-17T10:10:00Z",
    "completedAt": "2026-05-17T10:10:01Z"
  }
}
```

Error states:

- `404 ANALYSIS_NOT_FOUND`
- `404 REPORT_NOT_FOUND`
- `500 EXPORT_FAILED`

### POST /analyses/{analysis_id}/exports/pdf

Request body: none

Response:

```json
{
  "exportJob": {
    "id": "ex_124",
    "analysisId": "an_123",
    "reportId": "rp_123",
    "format": "pdf",
    "status": "completed",
    "downloadUrl": "/exports/ex_124/download",
    "createdAt": "2026-05-17T10:10:00Z",
    "completedAt": "2026-05-17T10:10:02Z"
  }
}
```

Error states:

- `404 ANALYSIS_NOT_FOUND`
- `404 REPORT_NOT_FOUND`
- `500 EXPORT_FAILED` if both the HTML-to-PDF renderer and built-in fallback renderer fail

### GET /exports/{export_id}

Request body: none

Response:

```json
{
  "exportJob": {}
}
```

Error states:

- `404 EXPORT_NOT_FOUND`

### GET /exports/{export_id}/download

Request body: none

Response:

- File response for completed export.

Error states:

- `404 EXPORT_NOT_FOUND`
- `409 EXPORT_NOT_READY`
- `410 EXPORT_FILE_MISSING`

## 7. Reliability Constraints

### File Size Limit

MVP limit:

- Maximum upload size: 25 MB.
- Maximum parsed rows: 100,000.
- Maximum parsed columns: 200.

Files above these limits return a clear error. Future versions can support background jobs and chunked processing.

### Supported File Types

Supported:

- `.csv`
- `.xlsx`

Not supported in MVP:

- `.xls`
- `.tsv`
- `.json`
- zipped files
- password-protected spreadsheets

### Invalid File Behavior

Invalid files are rejected before analysis. The product should show:

- What failed.
- Which file types are supported.
- Whether the user can retry.

No dataset should be marked analyzable after a parse failure.

### Missing Data Behavior

Missing data is profiled and reported, not automatically filled.

Analytics should:

- Ignore nulls for statistics where mathematically appropriate.
- Report sample sizes.
- Skip calculations with insufficient valid values.
- Add warnings to affected charts and insights.

### Datetime Parsing Issues

Datetime detection should use confidence thresholds. If a column partially parses as dates below the threshold, keep it as string/category and add a warning.

Do not silently coerce ambiguous dates into incorrect timelines.

### Encoding Problems

CSV parsing should attempt known encodings in order. If fallback encoding works, add a parse warning. If none works, return `UNSUPPORTED_ENCODING` or `PARSE_FAILED`.

### Duplicate Columns

Duplicate original headers should be disambiguated internally:

```text
Revenue
Revenue -> Revenue_2
```

The system must preserve original names for display and evidence. If headers are empty or cannot be made unique, return `DUPLICATE_COLUMNS_UNRESOLVABLE`.

### High-Cardinality Columns

High-cardinality columns should not become raw bar charts.

Rules:

- Treat near-unique string columns as `id` or `text`.
- Limit categorical charts to top N categories.
- Group the remainder as "Other" only when this does not hide important evidence.

### Empty Datasets

Reject when:

- No rows.
- No columns.
- All rows are empty.
- Header exists but no data rows exist.

Return `EMPTY_DATASET`.

### Determinism

The same input file should produce the same analysis output. If sampling is needed for charts, use stable sorting or a fixed seed and record the method in chart warnings or methodology.

## 8. Future Extensibility

### Authentication

Add user ownership without changing core analytics:

- Add `users` table.
- Add `owner_user_id` to datasets, analyses, reports, and export jobs.
- Protect routes with session/JWT middleware.
- Frontend adds login flow and user-specific history.

### Workspaces

Add workspace boundary:

- Add `workspaces` table.
- Add `workspace_id` to datasets and reports.
- Add membership and roles tables.
- Update queries to scope by workspace.

### Stripe Billing

Add billing around usage limits:

- Add `subscriptions` and `usage_events` tables.
- Count uploads, rows analyzed, exports, and optional AI rewrites.
- Gate large files, PDF export, and scheduled reports by plan.

### Google Sheets

Add a data connector layer:

```text
upload parser and sheets connector -> normalized dataframe -> same analysis pipeline
```

The pipeline should not care whether data came from a file or a connector.

### Database Connections

Add connector configs and query runs:

- `connections`
- `connection_credentials`
- `query_runs`

Query results should be converted into the same dataframe input contract as uploaded files.

### Scheduled Reports

Add background job execution:

- Store schedule definitions.
- Re-run connector/query ingestion.
- Generate new analysis and report version.
- Notify users when complete.

This likely requires a worker later, but the MVP should not start with one.

### AI Narrative Layer

Add after deterministic reporting is stable:

- Input: structured insight facts, evidence, report sections.
- Output: rewritten narrative only.
- Validation: preserve evidence values and reject unsupported additions.
- Fallback: deterministic prose remains available.

### Team Collaboration

Add collaborative objects:

- Comments on report sections.
- Shared report links.
- Role-based access.
- Version history.

This should sit on top of persisted reports and analyses, not inside the analytics pipeline.

## Buildability Notes

The MVP remains one-person buildable because:

- One frontend app.
- One backend app.
- One SQLite database.
- Local file storage.
- Synchronous analysis for constrained file sizes.
- Deterministic analytics before optional AI.
- JSON analysis artifacts instead of early over-normalization.
