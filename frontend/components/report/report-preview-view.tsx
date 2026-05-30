"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BarChart3,
  Download,
  FileText,
  ShieldCheck
} from "lucide-react";
import { ChartRenderer } from "@/components/charts/chart-renderer";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { Panel } from "@/components/ui/panel";
import { SectionLabel } from "@/components/ui/section-label";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  API_BASE_URL,
  apiGet,
  apiPost,
  normalizeUnknownError,
  toApiClientError,
  type ApiClientError
} from "@/lib/api-client";
import { loadIncludedChartIds } from "@/lib/report-selection";
import type { ChartSpec, ReportResponse } from "@/types/api";

type ReportPreviewViewProps = {
  datasetId: string;
};

type ReportState = {
  report: ReportResponse;
  charts: ChartSpec[];
};

export function ReportPreviewView({ datasetId }: ReportPreviewViewProps) {
  const [state, setState] = useState<ReportState | null>(null);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [exportError, setExportError] = useState<ApiClientError | null>(null);
  const [exportingFormat, setExportingFormat] = useState<"html" | "pdf" | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function generateReport() {
      try {
        const [report, charts] = await Promise.all([
          apiPost<ReportResponse>(`/api/datasets/${encodeURIComponent(datasetId)}/report`),
          apiGet<ChartSpec[]>(`/api/datasets/${encodeURIComponent(datasetId)}/charts`)
        ]);

        if (!cancelled) {
          setState({ report, charts });
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(normalizeUnknownError(caughtError));
        }
      }
    }

    void generateReport();

    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  const includedCharts = useMemo(() => {
    if (!state) {
      return [];
    }
    const chartById = new Map(state.charts.map((chart) => [chart.id, chart]));
    const selectedIds = new Set(loadIncludedChartIds(datasetId, state.charts));
    return state.report.chart_ids
      .filter((chartId) => selectedIds.has(chartId))
      .map((chartId) => chartById.get(chartId))
      .filter((chart): chart is ChartSpec => Boolean(chart));
  }, [datasetId, state]);

  if (error) {
    return (
      <ErrorState
        title={error.message}
        description={error.suggestedFix ?? "Return to the Insight Board and try generating the report again."}
        detail={error.technicalDetail ?? error.code}
        action={
          <Button asChild variant="outline">
            <Link href={`/studio/datasets/${datasetId}/insights`}>Back to insights</Link>
          </Button>
        }
      />
    );
  }

  if (!state) {
    return (
      <LoadingState
        title="Generating executive report"
        description="Assembling deterministic profile, chart, insight, and evidence objects into a memo."
      />
    );
  }

  const { report } = state;
  const dataQualityNotes = report.data_quality_notes ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Button asChild variant="quiet" size="sm">
            <Link href={`/studio/datasets/${datasetId}/insights`}>
              <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
              Back to insights
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href={`/studio/datasets/${datasetId}/charts`}>
              <BarChart3 className="mr-2 h-4 w-4" aria-hidden="true" />
              Back to charts
            </Link>
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            size="sm"
            disabled={Boolean(exportingFormat)}
            onClick={() => {
              void downloadReportExport(report.report_id, report.title, "html", setExportingFormat, setExportError);
            }}
          >
            <Download className="mr-2 h-4 w-4" aria-hidden="true" />
            {exportingFormat === "html" ? "Exporting" : "Export HTML"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={Boolean(exportingFormat)}
            onClick={() => {
              void downloadReportExport(report.report_id, report.title, "pdf", setExportingFormat, setExportError);
            }}
          >
            <FileText className="mr-2 h-4 w-4" aria-hidden="true" />
            {exportingFormat === "pdf" ? "Exporting" : "Export PDF"}
          </Button>
        </div>
      </div>

      {exportError ? (
        <ErrorState
          title={exportError.message}
          description={exportError.suggestedFix ?? "Try regenerating the report, then export again."}
          detail={exportError.technicalDetail ?? exportError.code}
        />
      ) : null}

      <article className="mx-auto max-w-5xl rounded-lg border bg-surface shadow-panel">
        <header className="border-b px-6 py-8 sm:px-10 sm:py-10">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone="success">Generated report</StatusBadge>
            <StatusBadge>{`${report.evidence_appendix.length} evidence refs`}</StatusBadge>
            <StatusBadge>{`${includedCharts.length} exhibits`}</StatusBadge>
          </div>
          <h1 className="mt-6 max-w-4xl text-heading-lg font-semibold text-foreground sm:text-display-md">
            {report.title}
          </h1>
          <p className="mt-5 max-w-3xl text-body text-muted-foreground">
            Generated from deterministic dataset profile, chart specs, insights, and evidence objects.
          </p>
        </header>

        <div className="space-y-10 px-6 py-8 sm:px-10 sm:py-10">
          <ReportTextSection eyebrow="Dataset overview" title="What was analyzed" body={report.dataset_overview} />
          <ReportTextSection eyebrow="Executive summary" title="Decision memo" body={report.executive_summary} prominent />

          <ReportListSection title="Key findings" items={report.key_findings} empty="No key findings crossed the deterministic report threshold." />
          <ReportListSection title="Risks" items={report.risks} empty="No risk section was generated from the available insights." />
          <ReportListSection title="Opportunities" items={report.opportunities} empty="No opportunity section was generated from the available insights." />
          <ReportListSection title="Recommended actions" items={report.recommendations} empty="No recommended actions were generated." />
          <ReportListSection title="Data quality notes" items={dataQualityNotes} empty="No data quality notes were generated." />

          <section className="space-y-5">
            <SectionLabel
              eyebrow="Exhibits"
              title="Charts included"
              description="Chart exhibits respect the local selections made in Chart Gallery and are shown only when matching backend chart specs exist."
            />
            {includedCharts.length > 0 ? (
              <div className="space-y-5">
                {includedCharts.slice(0, 4).map((chart, index) => (
                  <Panel key={chart.id} className="overflow-hidden">
                    <div className="border-b px-5 py-4">
                      <p className="text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
                        Exhibit {index + 1}
                      </p>
                      <h3 className="mt-2 text-heading-sm font-semibold text-foreground">{chart.title}</h3>
                      <p className="mt-2 text-body-sm text-muted-foreground">{chart.description}</p>
                    </div>
                    <div className="p-5">
                      <ChartRenderer chart={chart} />
                    </div>
                  </Panel>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No chart exhibits available"
                description="No selected chart IDs match the current chart recommendation response. Return to Chart Gallery to select exhibits for this report preview."
                icon={<BarChart3 className="h-4 w-4" aria-hidden="true" />}
                action={
                  <Button asChild variant="outline">
                    <Link href={`/studio/datasets/${datasetId}/charts`}>Select chart exhibits</Link>
                  </Button>
                }
              />
            )}
          </section>

          <EvidenceAppendix report={report} />
        </div>
      </article>
    </div>
  );
}

function ReportTextSection({
  eyebrow,
  title,
  body,
  prominent = false
}: {
  eyebrow: string;
  title: string;
  body: string;
  prominent?: boolean;
}) {
  return (
    <section className={prominent ? "rounded-lg border bg-surface-raised p-6" : ""}>
      <p className="text-caption font-medium uppercase tracking-[0.16em] text-muted-foreground">
        {eyebrow}
      </p>
      <h2 className="mt-2 text-heading-md font-semibold text-foreground">{title}</h2>
      <p className="mt-4 text-body text-muted-foreground">{body}</p>
    </section>
  );
}

function ReportListSection({
  title,
  items,
  empty
}: {
  title: string;
  items: string[];
  empty: string;
}) {
  return (
    <section>
      <h2 className="text-heading-md font-semibold text-foreground">{title}</h2>
      {items.length > 0 ? (
        <ol className="mt-4 space-y-3">
          {items.map((item, index) => (
            <li key={`${title}-${index}`} className="grid gap-3 rounded-lg border bg-surface-raised p-4 sm:grid-cols-[32px_minmax(0,1fr)]">
              <span className="flex h-8 w-8 items-center justify-center rounded-full border bg-surface text-caption font-semibold text-muted-foreground">
                {index + 1}
              </span>
              <p className="text-body-sm text-foreground">{item}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-3 rounded-lg border border-dashed bg-surface-raised px-4 py-3 text-body-sm text-muted-foreground">
          {empty}
        </p>
      )}
    </section>
  );
}

function EvidenceAppendix({ report }: { report: ReportResponse }) {
  return (
    <section>
      <SectionLabel
        eyebrow="Appendix"
        title="Evidence references"
        description="Each item is sourced from the deterministic insight evidence object."
        action={<ShieldCheck className="h-4 w-4 text-muted-foreground" aria-hidden="true" />}
      />
      {report.evidence_appendix.length > 0 ? (
        <div className="mt-5 space-y-3">
          {report.evidence_appendix.map((item, index) => (
            <details key={item.insight_id} className="rounded-lg border bg-surface-raised p-4">
              <summary className="cursor-pointer text-body-sm font-semibold text-foreground">
                Evidence {index + 1}: {item.insight_title}
              </summary>
              <div className="mt-4 grid gap-3 text-body-sm text-muted-foreground">
                <p>
                  <span className="font-medium text-foreground">Type:</span> {item.insight_type}
                </p>
                <p>
                  <span className="font-medium text-foreground">Calculation:</span>{" "}
                  {item.evidence.calculation}
                </p>
                <p>
                  <span className="font-medium text-foreground">Explanation:</span>{" "}
                  {item.evidence.explanation}
                </p>
              </div>
            </details>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No evidence appendix generated"
          description="The report did not include insight evidence references."
          icon={<FileText className="h-4 w-4" aria-hidden="true" />}
        />
      )}
    </section>
  );
}

async function downloadReportExport(
  reportId: string,
  reportTitle: string,
  format: "html" | "pdf",
  setExportingFormat: (value: "html" | "pdf" | null) => void,
  setExportError: (value: ApiClientError | null) => void
) {
  setExportingFormat(format);
  setExportError(null);

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/reports/${encodeURIComponent(reportId)}/export/${format}`,
      { headers: { Accept: format === "html" ? "text/html" : "application/pdf" } }
    );
    if (!response.ok) {
      throw await toApiClientError(response);
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${safeFileName(reportTitle)}.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (caughtError) {
    setExportError(normalizeUnknownError(caughtError));
  } finally {
    setExportingFormat(null);
  }
}

function safeFileName(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "insightpilot-report";
}
