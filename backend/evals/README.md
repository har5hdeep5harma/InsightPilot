# InsightPilot Evaluation Framework

This folder contains a deterministic evaluation harness for the InsightPilot MVP. It is designed to prove that the product generates reliable, evidence-backed outputs from a realistic SaaS dataset.

## Files

- `expected_insights.json`: expected dataset facts, profiling outcomes, generated insight expectations, and report/export thresholds.
- `run_evals.py`: executes the sample dataset through the real FastAPI/backend pipeline using an in-memory SQLite database.
- `eval_results.json`: latest scoring output from the eval runner.

## What The Eval Covers

The runner scores ten areas:

1. Column role detection
2. Missing value detection
3. Duplicate detection
4. Outlier detection
5. Trend detection
6. Top category insight
7. Concentration insight
8. Correlation insight
9. Report generation
10. Export generation

Insight-level checks include:

- correctness
- evidence present
- no unsupported claim shape
- useful recommendation
- severity appropriate
- confidence reasonable

## Run

From `backend/`:

```bash
python evals/run_evals.py
```

The runner writes:

```text
backend/evals/eval_results.json
```

It exits with status code `0` when the overall score meets the threshold in `expected_insights.json`.

## Approach

The eval intentionally uses the same code paths as the product:

- upload parsing through `POST /api/datasets/upload`
- profiling through `GET /api/datasets/{dataset_id}/profile`
- chart recommendation through `GET /api/datasets/{dataset_id}/charts`
- insight generation through `GET /api/datasets/{dataset_id}/insights`
- report generation through `POST /api/datasets/{dataset_id}/report`
- HTML/PDF export routes through `GET /api/reports/{report_id}/export/*`

The SaaS dataset is synthetic but not arbitrary. It encodes known business patterns, quality issues, outliers, and segment differences. The eval verifies both the encoded data facts and the generated product outputs.

PDF export should return a downloadable PDF. When WeasyPrint is not installed, InsightPilot uses its built-in fallback PDF renderer, so the eval still expects a valid PDF response.
