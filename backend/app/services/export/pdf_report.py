from __future__ import annotations

from app.models.report import Report
from app.services.export.html_report import render_report_html, report_html_filename


def render_report_pdf(report: Report) -> bytes:
    try:
        from weasyprint import HTML
    except Exception as exc:  # pragma: no cover - import behavior depends on host PDF stack.
        return _render_basic_pdf(report, fallback_reason=f"WeasyPrint unavailable: {exc}")

    html = render_report_html(report)
    try:
        pdf_bytes = HTML(string=html).write_pdf()
    except Exception as exc:  # pragma: no cover - depends on local native PDF stack.
        return _render_basic_pdf(report, fallback_reason=f"WeasyPrint render failed: {exc}")

    if not isinstance(pdf_bytes, bytes) or not pdf_bytes.startswith(b"%PDF"):
        return _render_basic_pdf(report, fallback_reason="WeasyPrint returned non-PDF output.")

    return pdf_bytes


def report_pdf_filename(report: Report) -> str:
    return report_html_filename(report).removesuffix(".html") + ".pdf"


def _render_basic_pdf(report: Report, *, fallback_reason: str) -> bytes:
    lines = _pdf_lines(report, fallback_reason=fallback_reason)
    pages = _paginate(lines, max_lines=48)
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    page_object_ids: list[int] = []
    content_object_ids: list[int] = []
    for page_lines in pages:
        content = _page_content(page_lines)
        content_object_id = len(objects) + 2
        page_object_id = len(objects) + 1
        page_object_ids.append(page_object_id)
        content_object_ids.append(content_object_id)
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_object_id} 0 R >>"
            ).encode("ascii")
        )
        objects.append(
            b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream"
        )

    kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_ids)} >>".encode("ascii")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def _pdf_lines(report: Report, *, fallback_reason: str) -> list[str]:
    lines = [
        "InsightPilot Executive Report",
        report.title,
        f"Generated {report.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "PDF rendering note",
        "This PDF was generated with InsightPilot's built-in fallback renderer.",
        fallback_reason,
        "",
        "Dataset overview",
        report.dataset_overview,
        "",
        "Executive summary",
        report.executive_summary,
        "",
    ]
    lines.extend(_section_lines("Key findings", report.key_findings))
    lines.extend(_section_lines("Risks", report.risks))
    lines.extend(_section_lines("Opportunities", report.opportunities))
    lines.extend(_section_lines("Recommended actions", report.recommendations))
    lines.extend(_section_lines("Data quality notes", report.data_quality_notes))
    lines.append("Charts included")
    if report.charts:
        for index, chart in enumerate(report.charts[:8], start=1):
            lines.append(f"{index}. {chart.title}")
            lines.append(f"   {chart.description}")
            lines.append(
                f"   Type: {chart.chart_type.value}; rows: {len(chart.chart_data)}; reasoning: {chart.reasoning}"
            )
            summary = _chart_summary(chart.chart_data, chart.x_column, chart.y_column)
            if summary:
                lines.append(f"   Data note: {summary}")
    else:
        lines.append("No chart exhibits were attached to this report.")
    lines.append("")
    lines.append("Evidence appendix")
    if report.evidence_appendix:
        for index, item in enumerate(report.evidence_appendix, start=1):
            evidence = item.evidence
            lines.append(f"{index}. {item.insight_title}")
            lines.append(f"   Type: {item.insight_type}")
            lines.append(f"   Calculation: {evidence.get('calculation', 'Not provided')}")
            lines.append(f"   Value: {evidence.get('value', 'Not provided')}")
            lines.append(f"   Explanation: {evidence.get('explanation', 'Not provided')}")
    else:
        lines.append("No evidence appendix was generated for this report.")
    return lines


def _section_lines(title: str, items: list[str]) -> list[str]:
    lines = [title]
    if not items:
        lines.append(f"No {title.lower()} were generated for this report.")
    else:
        for index, item in enumerate(items, start=1):
            lines.append(f"{index}. {item}")
    lines.append("")
    return lines


def _chart_summary(
    chart_data: list[dict[str, object]],
    x_column: str | None,
    y_column: str | None,
) -> str | None:
    if not chart_data:
        return None
    if not x_column or not y_column:
        return f"{len(chart_data)} backend-provided chart rows."

    ranked: list[tuple[str, float]] = []
    for row in chart_data:
        try:
            value = float(row.get(y_column, row.get(x_column, 0)) or 0)
        except (TypeError, ValueError):
            continue
        label = str(row.get(x_column, row.get(y_column, "Unknown")))
        ranked.append((label, value))
    if not ranked:
        return f"{len(chart_data)} backend-provided chart rows."

    ranked.sort(key=lambda item: item[1], reverse=True)
    label, value = ranked[0]
    return f"Highest displayed value is {value:,.2f} for {label}."


def _paginate(lines: list[str], *, max_lines: int) -> list[list[str]]:
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(_wrap_line(line, width=92))

    pages = [
        wrapped[index : index + max_lines]
        for index in range(0, len(wrapped), max_lines)
    ]
    return pages or [["InsightPilot Executive Report"]]


def _wrap_line(line: str, *, width: int) -> list[str]:
    ascii_line = line.encode("latin-1", errors="replace").decode("latin-1")
    if not ascii_line:
        return [""]
    words = ascii_line.split()
    output: list[str] = []
    current = ""
    for word in words:
        proposed = f"{current} {word}".strip()
        if len(proposed) <= width:
            current = proposed
        else:
            output.append(current)
            current = word
    if current:
        output.append(current)
    return output


def _page_content(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 10 Tf", "14 TL", "54 790 Td"]
    for index, line in enumerate(lines):
        if index:
            commands.append("T*")
        commands.append(f"({_pdf_escape(line)}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def _pdf_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )
