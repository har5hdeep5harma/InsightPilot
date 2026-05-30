# InsightPilot Backend

FastAPI service for deterministic dataset parsing, profiling, chart recommendation, insight generation, report generation, and exports.

## Local Development

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Health check:

```text
http://localhost:8000/health
```

## Tests

```bash
pytest
```

