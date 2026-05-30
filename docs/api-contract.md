# InsightPilot API Contract

The full route contract is currently documented in [technical-architecture.md](technical-architecture.md).

This file is reserved for the implementation-phase OpenAPI notes and route-level examples as endpoints are added.

## Implemented Dataset Routes

### POST /api/datasets/upload

Accepts multipart form data:

- `file`: `.csv` or `.xlsx`

Successful response includes:

- `dataset_id`
- `filename`
- `row_count`
- `column_count`
- normalized `columns`
- first 20 `preview_rows`
- parser `warnings`

Rejected uploads return:

```json
{
  "error": {
    "code": "UNSUPPORTED_FILE_TYPE",
    "message": "Only CSV and XLSX files are supported.",
    "technical_detail": "Received file extension '.txt'.",
    "suggested_fix": "Upload a .csv or .xlsx file exported from your spreadsheet tool.",
    "details": {}
  }
}
```

Implemented validation includes unsupported file type, empty file, local size limit, malformed CSV, encoding fallback, missing headers, duplicate column headers, and empty datasets.

### GET /api/datasets/{dataset_id}

Returns uploaded dataset metadata, normalized columns, parser warnings, and processing status.

### GET /api/datasets/{dataset_id}/preview

Query params:

- `limit`: default `20`, max `200`
- `offset`: default `0`

Returns preview rows from the persisted parsed dataset artifact.

### GET /api/datasets/{dataset_id}/profile

Profiles the persisted parsed dataset artifact and returns a structured `DatasetProfile`.

The endpoint computes and persists:

- row and column counts
- duplicate row count
- memory usage
- per-column inferred type and role
- missing and unique counts/percentages
- top values
- numeric min, max, mean, median, and standard deviation
- datetime min and max where applicable
- profile warnings
- quality score from 0 to 100

Implemented inferred types:

- `numeric`
- `categorical`
- `datetime`
- `boolean`
- `text`
- `unknown`

Implemented roles:

- `metric`
- `dimension`
- `datetime`
- `id`
- `text`
- `ignored`

The profiler is deterministic and does not use an LLM.

### GET /api/datasets/{dataset_id}/charts

Profiles the dataset if needed, generates deterministic chart recommendations, persists the generated chart specs, and returns directly renderable chart data.

Response body:

```json
[
  {
    "id": "chart_abc123",
    "dataset_id": "ds_123",
    "title": "Revenue over time",
    "chart_type": "line",
    "x_column": "order_date",
    "y_column": "revenue",
    "group_by": null,
    "description": "Tracks Revenue by Order Date.",
    "reasoning": "A datetime column and a numeric metric support a time series view.",
    "priority": 1,
    "chart_data": [
      {
        "order_date": "2026-01-01",
        "revenue": 1200
      }
    ]
  }
]
```

Implemented chart types:

- `line`
- `bar`
- `horizontal_bar`
- `histogram`
- `scatter`
- `correlation_heatmap`
- `box_plot`
- `stacked_bar`

The endpoint returns an empty list when the dataset has too few usable non-ID columns. It does not emit placeholder chart specs.

### GET /api/datasets/{dataset_id}/insights

Profiles the dataset if needed, generates chart specs if needed, then creates deterministic evidence-backed insights from computed data.

Response body:

```json
[
  {
    "id": "ins_abc123",
    "dataset_id": "ds_123",
    "title": "Revenue is concentrated in West",
    "summary": "West contributes 64.2% of total Revenue across Region.",
    "insight_type": "concentration",
    "severity": "medium",
    "confidence": 0.84,
    "evidence": {
      "type": "comparison",
      "column": "region",
      "columns": ["region", "revenue"],
      "metric": "top_category_share",
      "value": 64.2,
      "comparison_value": "share of total",
      "values": {
        "top_category": "West",
        "top_value": 10400,
        "total_value": 16200
      },
      "comparison_values": {},
      "rows_affected": 120,
      "calculation": "sum(revenue) grouped by region",
      "explanation": "The top category share is computed directly from grouped totals."
    },
    "recommendation": "Review whether performance depends too heavily on this segment before making broad assumptions from aggregate results.",
    "related_columns": ["region", "revenue"],
    "related_chart_id": "chart_abc123"
  }
]
```

Implemented insight types:

- `dataset_quality`
- `trend`
- `top_category`
- `concentration`
- `outlier`
- `correlation`
- `distribution`
- `missing_data_risk`
- `segment_difference`

Implemented severities:

- `low`
- `medium`
- `high`

The endpoint avoids weak evidence and returns only insights backed by deterministic calculations.

### POST /api/datasets/{dataset_id}/report

Generates and persists a deterministic executive memo from the dataset profile, chart specs, deterministic insights, and evidence objects.

Response body:

```json
{
  "report_id": "report_abc123",
  "title": "Executive Analysis Memo: sales.csv",
  "dataset_overview": "The uploaded dataset `sales.csv` contains 1,000 rows and 12 columns...",
  "executive_summary": "The strongest finding is: Revenue increased from the first period to the last period...",
  "key_findings": [
    "Revenue increased over time. Evidence: ..."
  ],
  "risks": [
    "Cost is missing in 35.0% of rows..."
  ],
  "opportunities": [
    "Use the finding `Revenue increased over time` to prioritize follow-up analysis..."
  ],
  "recommendations": [
    "Check whether this movement aligns with known seasonality, campaigns, or operational changes..."
  ],
  "data_quality_notes": [
    "Quality score: 97.0/100.",
    "Duplicate rows detected: 0."
  ],
  "evidence_appendix": [
    {
      "insight_id": "ins_abc123",
      "insight_title": "Revenue increased over time",
      "insight_type": "trend",
      "evidence": {}
    }
  ],
  "chart_ids": ["chart_abc123"]
}
```

The memo generator uses deterministic templates by default. Optional AI narrative polishing is behind `ENABLE_AI_NARRATIVE=true`. When enabled with `AI_NARRATIVE_API_KEY`, the backend sends only structured deterministic report facts to an OpenAI-compatible provider, requires JSON output, validates list lengths and unsupported numeric values, logs the result, and falls back to the deterministic report if validation or provider calls fail.

The product does not require an API key. With `ENABLE_AI_NARRATIVE=false` or no provider key configured, report generation uses deterministic templates only.

### GET /api/reports/{report_id}

Returns a previously generated report with the same response shape as `POST /api/datasets/{dataset_id}/report`.

Error states:

- `404 REPORT_NOT_FOUND`

### GET /api/reports/{report_id}/export/html

Returns a standalone downloadable HTML report generated from the persisted report model.

Response:

- `Content-Type: text/html; charset=utf-8`
- `Content-Disposition: attachment; filename="executive-analysis-memo-example.html"`
- Body: printable HTML document with title, generated timestamp, dataset overview, executive summary, key findings, risks, opportunities, recommendations, data quality notes, and evidence appendix.

Error states:

- `404 REPORT_NOT_FOUND`

### GET /api/reports/{report_id}/export/pdf

Returns a downloadable PDF report generated from the same persisted report model and standalone HTML renderer used by HTML export.

Response:

- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="executive-analysis-memo-example.pdf"`
- Body: printable PDF document with title, generated timestamp, dataset overview, executive summary, key findings, risks, opportunities, recommendations, data quality notes, and evidence appendix.

PDF export first tries WeasyPrint so the PDF can mirror the standalone HTML report, including chart exhibits. If WeasyPrint or its native rendering stack is unavailable, InsightPilot falls back to a built-in PDF renderer that still returns a downloadable report with report sections, chart exhibit summaries, and the evidence appendix.

Error states:

- `404 REPORT_NOT_FOUND`
