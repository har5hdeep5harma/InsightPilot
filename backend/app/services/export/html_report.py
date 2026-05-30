from __future__ import annotations

from html import escape
from re import sub

from app.models.chart import ChartSpec
from app.models.report import EvidenceAppendixItem, Report


def render_report_html(report: Report) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(report.title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #111827;
      --muted: #5f6b7a;
      --line: #e5e7eb;
      --surface: #f8fafc;
      --accent: #1d4ed8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #ffffff;
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
      line-height: 1.65;
    }}
    main {{
      max-width: 920px;
      margin: 0 auto;
      padding: 56px 48px 72px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 28px;
      margin-bottom: 34px;
    }}
    .eyebrow {{
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    h1 {{
      font-size: 38px;
      line-height: 1.08;
      letter-spacing: 0;
      margin: 12px 0 14px;
    }}
    h2 {{
      border-top: 1px solid var(--line);
      font-size: 21px;
      line-height: 1.25;
      margin: 34px 0 14px;
      padding-top: 24px;
    }}
    p {{ margin: 0 0 12px; }}
    ol {{ margin: 12px 0 0; padding-left: 22px; }}
    li {{ margin: 10px 0; }}
    .muted {{ color: var(--muted); }}
    .summary {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 18px 20px;
    }}
    .appendix-item {{
      border: 1px solid var(--line);
      border-radius: 10px;
      margin-top: 12px;
      padding: 16px 18px;
      break-inside: avoid;
    }}
    .chart-card {{
      border: 1px solid var(--line);
      border-radius: 10px;
      margin-top: 14px;
      padding: 16px 18px;
      break-inside: avoid;
    }}
    .chart-meta {{
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 12px;
    }}
    .chart-svg {{
      display: block;
      width: 100%;
      height: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
    }}
    .chart-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }}
    .chart-table th,
    .chart-table td {{
      border-top: 1px solid var(--line);
      padding: 8px;
      text-align: left;
      vertical-align: top;
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: minmax(120px, 180px) minmax(0, 1fr) 86px;
      gap: 10px;
      align-items: center;
      margin-top: 8px;
      font-size: 12px;
    }}
    .bar-track {{
      height: 12px;
      border-radius: 999px;
      background: #e5e7eb;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      border-radius: 999px;
      background: var(--accent);
    }}
    .heatmap-grid {{
      display: grid;
      gap: 3px;
      overflow-x: auto;
      font-size: 11px;
    }}
    .heatmap-cell {{
      min-height: 34px;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
    }}
    .appendix-title {{
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .kv {{
      display: grid;
      grid-template-columns: 150px minmax(0, 1fr);
      gap: 10px;
      border-top: 1px solid var(--line);
      padding-top: 9px;
      margin-top: 9px;
    }}
    .key {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    code {{
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    @page {{
      size: A4;
      margin: 18mm 16mm;
    }}
    @media print {{
      body {{ font-size: 12px; }}
      main {{ padding: 24px; max-width: none; }}
      h1 {{ font-size: 28px; }}
      h2 {{ font-size: 17px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="eyebrow">InsightPilot Executive Report</div>
      <h1>{_e(report.title)}</h1>
      <p class="muted">Generated {_e(report.created_at.strftime("%Y-%m-%d %H:%M UTC"))}</p>
    </header>

    <section>
      <h2>Dataset overview</h2>
      <p>{_e(report.dataset_overview)}</p>
    </section>

    <section>
      <h2>Executive summary</h2>
      <div class="summary">{_paragraph(report.executive_summary)}</div>
    </section>

    {_list_section("Key findings", report.key_findings)}
    {_list_section("Risks", report.risks)}
    {_list_section("Opportunities", report.opportunities)}
    {_list_section("Recommended actions", report.recommendations)}
    {_list_section("Data quality notes", report.data_quality_notes)}
    {_chart_exhibits(report.charts)}
    {_evidence_appendix(report.evidence_appendix)}
  </main>
</body>
</html>
"""


def report_html_filename(report: Report) -> str:
    base = sub(r"[^a-zA-Z0-9]+", "-", report.title).strip("-").lower()
    return f"{base or 'insightpilot-report'}.html"


def _list_section(title: str, items: list[str]) -> str:
    if not items:
        return (
            f"<section><h2>{_e(title)}</h2>"
            f'<p class="muted">No {_e(title.lower())} were generated for this report.</p></section>'
        )

    list_items = "\n".join(f"<li>{_e(item)}</li>" for item in items)
    return f"<section><h2>{_e(title)}</h2><ol>{list_items}</ol></section>"


def _chart_exhibits(charts: list[ChartSpec]) -> str:
    if not charts:
        return (
            "<section><h2>Charts included</h2>"
            '<p class="muted">No chart exhibits were attached to this report.</p></section>'
        )

    rendered = "\n".join(_chart_card(chart, index) for index, chart in enumerate(charts[:8], start=1))
    return f"<section><h2>Charts included</h2>{rendered}</section>"


def _chart_card(chart: ChartSpec, index: int) -> str:
    return f"""
<article class="chart-card">
  <div class="eyebrow">Exhibit {index}</div>
  <h3>{_e(chart.title)}</h3>
  <p class="chart-meta">{_e(chart.description)}</p>
  {_chart_visual(chart)}
  <div class="kv"><div class="key">Reasoning</div><div>{_e(chart.reasoning)}</div></div>
</article>
"""


def _chart_visual(chart: ChartSpec) -> str:
    chart_type = chart.chart_type.value
    if chart_type in {"bar", "horizontal_bar", "histogram"}:
        return _bar_visual(chart)
    if chart_type == "line":
        return _line_visual(chart)
    if chart_type == "scatter":
        return _scatter_visual(chart)
    if chart_type == "correlation_heatmap":
        return _heatmap_visual(chart)
    if chart_type == "box_plot":
        return _box_plot_visual(chart)
    if chart_type == "stacked_bar":
        return _table_visual(chart, limit=8)
    return _table_visual(chart, limit=8)


def _bar_visual(chart: ChartSpec) -> str:
    label_key = chart.y_column if chart.chart_type.value == "horizontal_bar" else chart.x_column
    value_key = chart.x_column if chart.chart_type.value == "horizontal_bar" else chart.y_column
    if not label_key or not value_key:
        return _table_visual(chart, limit=8)

    rows = [
        (str(row.get(label_key, "Unknown")), _number(row.get(value_key)))
        for row in chart.chart_data[:12]
    ]
    rows = [(label, value) for label, value in rows if value is not None]
    if not rows:
        return _table_visual(chart, limit=8)

    maximum = max(abs(value) for _, value in rows) or 1
    rendered = "\n".join(
        f"""
<div class="bar-row">
  <div>{_e(label)}</div>
  <div class="bar-track"><div class="bar-fill" style="width: {max(2, min(100, abs(value) / maximum * 100)):.2f}%"></div></div>
  <div>{_e(_string(value))}</div>
</div>
"""
        for label, value in rows
    )
    return f"<div>{rendered}</div>"


def _line_visual(chart: ChartSpec) -> str:
    x_key = chart.x_column
    y_key = chart.y_column
    if not x_key or not y_key:
        return _table_visual(chart, limit=8)

    values = [
        (str(row.get(x_key, "")), _number(row.get(y_key)))
        for row in chart.chart_data
    ]
    values = [(label, value) for label, value in values if value is not None]
    if len(values) < 2:
        return _table_visual(chart, limit=8)

    width = 760
    height = 260
    left = 54
    right = 22
    top = 18
    bottom = 42
    y_values = [value for _, value in values]
    y_min = min(y_values)
    y_max = max(y_values)
    span = y_max - y_min or 1
    x_span = max(1, len(values) - 1)

    points = []
    for index, (_, value) in enumerate(values):
        x = left + index / x_span * (width - left - right)
        y = top + (1 - (value - y_min) / span) * (height - top - bottom)
        points.append((x, y))

    polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    first_label = values[0][0]
    last_label = values[-1][0]
    return f"""
<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="{_e(chart.title)}">
  <line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="#e5e7eb" />
  <line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#e5e7eb" />
  <polyline points="{polyline}" fill="none" stroke="#1d4ed8" stroke-width="3" />
  <circle cx="{points[0][0]:.2f}" cy="{points[0][1]:.2f}" r="4" fill="#1d4ed8" />
  <circle cx="{points[-1][0]:.2f}" cy="{points[-1][1]:.2f}" r="4" fill="#1d4ed8" />
  <text x="{left}" y="{height - 14}" fill="#5f6b7a" font-size="12">{_e(first_label)}</text>
  <text x="{width - right}" y="{height - 14}" text-anchor="end" fill="#5f6b7a" font-size="12">{_e(last_label)}</text>
  <text x="8" y="{top + 4}" fill="#5f6b7a" font-size="12">{_e(_string(y_max))}</text>
  <text x="8" y="{height - bottom}" fill="#5f6b7a" font-size="12">{_e(_string(y_min))}</text>
</svg>
"""


def _scatter_visual(chart: ChartSpec) -> str:
    x_key = chart.x_column
    y_key = chart.y_column
    if not x_key or not y_key:
        return _table_visual(chart, limit=8)

    points_raw = [
        (_number(row.get(x_key)), _number(row.get(y_key)))
        for row in chart.chart_data[:500]
    ]
    points_raw = [(x, y) for x, y in points_raw if x is not None and y is not None]
    if len(points_raw) < 2:
        return _table_visual(chart, limit=8)

    width = 760
    height = 260
    left = 54
    right = 22
    top = 18
    bottom = 42
    x_values = [x for x, _ in points_raw]
    y_values = [y for _, y in points_raw]
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    x_span = x_max - x_min or 1
    y_span = y_max - y_min or 1
    circles = []
    for x_value, y_value in points_raw:
        x = left + (x_value - x_min) / x_span * (width - left - right)
        y = top + (1 - (y_value - y_min) / y_span) * (height - top - bottom)
        circles.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.4" fill="#1d4ed8" opacity="0.45" />')

    return f"""
<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="{_e(chart.title)}">
  <line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="#e5e7eb" />
  <line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#e5e7eb" />
  {"".join(circles)}
  <text x="{left}" y="{height - 14}" fill="#5f6b7a" font-size="12">{_e(_string(x_min))}</text>
  <text x="{width - right}" y="{height - 14}" text-anchor="end" fill="#5f6b7a" font-size="12">{_e(_string(x_max))}</text>
  <text x="8" y="{top + 4}" fill="#5f6b7a" font-size="12">{_e(_string(y_max))}</text>
  <text x="8" y="{height - bottom}" fill="#5f6b7a" font-size="12">{_e(_string(y_min))}</text>
</svg>
"""


def _heatmap_visual(chart: ChartSpec) -> str:
    metrics = sorted(
        {
            str(value)
            for row in chart.chart_data
            for value in (row.get("metric_x"), row.get("metric_y"))
            if value
        }
    )
    if not metrics:
        return _table_visual(chart, limit=8)

    cells = ["<div></div>"]
    cells.extend(f'<div class="key">{_e(metric)}</div>' for metric in metrics)
    for y_metric in metrics:
        cells.append(f'<div class="key">{_e(y_metric)}</div>')
        for x_metric in metrics:
            value = _number(
                next(
                    (
                        row.get("correlation")
                        for row in chart.chart_data
                        if row.get("metric_x") == x_metric and row.get("metric_y") == y_metric
                    ),
                    0,
                )
            ) or 0
            alpha = 0.12 + min(0.72, abs(value) * 0.72)
            color = f"rgba(29, 78, 216, {alpha:.3f})" if value >= 0 else f"rgba(217, 119, 6, {alpha:.3f})"
            text_color = "#ffffff" if abs(value) > 0.65 else "#111827"
            cells.append(
                f'<div class="heatmap-cell" style="background:{color};color:{text_color}">{value:.2f}</div>'
            )
    return (
        f'<div class="heatmap-grid" style="grid-template-columns: 130px repeat({len(metrics)}, minmax(74px, 1fr));">'
        + "\n".join(cells)
        + "</div>"
    )


def _box_plot_visual(chart: ChartSpec) -> str:
    return _table_visual(chart, limit=8)


def _table_visual(chart: ChartSpec, *, limit: int) -> str:
    rows = chart.chart_data[:limit]
    if not rows:
        return '<p class="muted">No chart data was returned for this exhibit.</p>'

    keys = list(rows[0].keys())[:6]
    header = "".join(f"<th>{_e(key)}</th>" for key in keys)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{_e(row.get(key))}</td>" for key in keys) + "</tr>"
        for row in rows
    )
    return f'<table class="chart-table"><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'


def _evidence_appendix(items: list[EvidenceAppendixItem]) -> str:
    if not items:
        return (
            '<section><h2>Evidence appendix</h2>'
            '<p class="muted">No evidence appendix was generated for this report.</p></section>'
        )

    rendered_items = "\n".join(_evidence_item(item, index) for index, item in enumerate(items, start=1))
    return f"<section><h2>Evidence appendix</h2>{rendered_items}</section>"


def _evidence_item(item: EvidenceAppendixItem, index: int) -> str:
    evidence = item.evidence
    columns = evidence.get("columns") or []
    if evidence.get("column") and evidence["column"] not in columns:
        columns = [evidence["column"], *columns]

    return f"""
<article class="appendix-item">
  <div class="appendix-title">Evidence {index}: {_e(item.insight_title)}</div>
  <div class="kv"><div class="key">Insight type</div><div>{_e(item.insight_type)}</div></div>
  <div class="kv"><div class="key">Calculation</div><div><code>{_e(_string(evidence.get("calculation")))}</code></div></div>
  <div class="kv"><div class="key">Columns</div><div>{_e(", ".join(_string(column) for column in columns) or "Not specified")}</div></div>
  <div class="kv"><div class="key">Value</div><div>{_e(_string(evidence.get("value")))}</div></div>
  <div class="kv"><div class="key">Comparison</div><div>{_e(_string(evidence.get("comparison_value")))}</div></div>
  <div class="kv"><div class="key">Rows affected</div><div>{_e(_string(evidence.get("rows_affected")))}</div></div>
  <div class="kv"><div class="key">Explanation</div><div>{_e(_string(evidence.get("explanation")))}</div></div>
</article>
"""


def _paragraph(value: str) -> str:
    return f"<p>{_e(value)}</p>"


def _string(value: object) -> str:
    if value is None:
        return "Not provided"
    if isinstance(value, float):
        return f"{value:,.3f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, dict):
        return ", ".join(f"{key}: {_string(item)}" for key, item in value.items()) or "Not provided"
    if isinstance(value, list):
        return ", ".join(_string(item) for item in value) or "Not provided"
    return str(value)


def _number(value: object) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric == numeric else None


def _e(value: object) -> str:
    return escape(_string(value), quote=True)
