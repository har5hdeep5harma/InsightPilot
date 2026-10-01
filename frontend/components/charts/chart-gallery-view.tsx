"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, BarChart3, Check, Eye, EyeOff } from "lucide-react";
import { ChartRenderer } from "@/components/charts/chart-renderer";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { Panel } from "@/components/ui/panel";
import { SectionLabel } from "@/components/ui/section-label";
import { StatusBadge } from "@/components/ui/status-badge";
import { apiGet, normalizeUnknownError, type ApiClientError } from "@/lib/api-client";
import {
  loadIncludedChartIds,
  saveIncludedChartIds
} from "@/lib/report-selection";
import type { ChartSpec } from "@/types/api";

type ChartGalleryViewProps = {
  datasetId: string;
};

export function ChartGalleryView({ datasetId }: ChartGalleryViewProps) {
  const [charts, setCharts] = useState<ChartSpec[] | null>(null);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [includedChartIds, setIncludedChartIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;

    async function loadCharts() {
      try {
        const response = await apiGet<ChartSpec[]>(
          `/api/datasets/${encodeURIComponent(datasetId)}/charts`
        );
        if (!cancelled) {
          setCharts(response);
          setIncludedChartIds(new Set(loadIncludedChartIds(datasetId, response)));
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(normalizeUnknownError(caughtError));
        }
      }
    }

    void loadCharts();

    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  const visibleCharts = useMemo(() => {
    return charts?.filter((chart) => hasUsableChartData(chart)) ?? [];
  }, [charts]);

  const includedCount = useMemo(() => includedChartIds.size, [includedChartIds]);

  function toggleIncluded(chartId: string) {
    setIncludedChartIds((current) => {
      const next = new Set(current);
      if (next.has(chartId)) {
        next.delete(chartId);
      } else {
        next.add(chartId);
      }
      saveIncludedChartIds(datasetId, Array.from(next));
      return next;
    });
  }

  if (error) {
    return (
      <ErrorState
        title={error.message}
        description={error.suggestedFix ?? "Return to the profile screen and try again."}
        detail={error.technicalDetail ?? error.code}
        action={
          <Button asChild variant="outline">
            <Link href={`/studio/datasets/${datasetId}/profile`}>Back to profile</Link>
          </Button>
        }
      />
    );
  }

  if (!charts) {
    return (
      <LoadingState
        title="Recommending charts"
        description="Evaluating detected roles and preparing backend chart specs."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button asChild variant="quiet" size="sm">
          <Link href={`/studio/datasets/${datasetId}/profile`}>
            <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
            Back to profile
          </Link>
        </Button>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge>{`${includedCount} selected for report`}</StatusBadge>
          <Button asChild size="sm">
            <Link href={`/studio/datasets/${datasetId}/insights`}>
              Generate insights
              <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </div>

      {visibleCharts.length === 0 ? (
        <EmptyState
          title="No useful charts recommended"
          description="The backend did not find enough usable signal in this dataset to recommend a meaningful chart."
          icon={<BarChart3 className="h-4 w-4" aria-hidden="true" />}
        />
      ) : (
        <div className="grid gap-5">
          {visibleCharts.map((chart) => (
            <Panel key={chart.id} as="article" className="overflow-hidden">
              <div className="border-b px-5 py-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <SectionLabel
                    title={chart.title}
                    description={chart.description}
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge>{chart.chart_type.replaceAll("_", " ")}</StatusBadge>
                    <Button
                      type="button"
                      variant={includedChartIds.has(chart.id) ? "secondary" : "outline"}
                      size="sm"
                      onClick={() => toggleIncluded(chart.id)}
                    >
                      {includedChartIds.has(chart.id) ? (
                        <>
                          <Check className="mr-2 h-4 w-4" aria-hidden="true" />
                          Selected
                        </>
                      ) : (
                        <>
                          <EyeOff className="mr-2 h-4 w-4" aria-hidden="true" />
                          Omitted
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
              <div className="grid gap-0 xl:grid-cols-[minmax(0,1fr)_340px]">
                <div className="p-5">
                  <ChartRenderer chart={chart} />
                </div>
                <aside className="border-t bg-surface-raised p-5 xl:border-l xl:border-t-0">
                  <div className="flex items-center gap-2 text-body-sm font-semibold text-foreground">
                    <Eye className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    Interpretation
                  </div>
                  <p className="mt-3 text-body-sm text-muted-foreground">
                    {interpretChart(chart)}
                  </p>
                  <div className="mt-5 grid gap-3 text-body-sm text-muted-foreground sm:grid-cols-2 xl:grid-cols-1">
                    <ChartFact label="X column" value={chart.x_column ?? "Not used"} />
                    <ChartFact label="Y column" value={chart.y_column ?? "Not used"} />
                    <ChartFact label="Group by" value={chart.group_by ?? "None"} />
                    <ChartFact label="Rows" value={chart.chart_data.length.toLocaleString()} />
                  </div>
                  <div className="mt-5 rounded-md border bg-surface px-3 py-3">
                    <p className="text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
                      Recommendation logic
                    </p>
                    <p className="mt-2 text-body-sm text-muted-foreground">{chart.reasoning}</p>
                    <p className="mt-3 border-t pt-3 text-caption text-muted-foreground">
                      Selection is saved locally and applied when the report preview embeds chart exhibits.
                    </p>
                  </div>
                </aside>
              </div>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}

function interpretChart(chart: ChartSpec) {
  if (!chart.chart_data.length) {
    return "The backend returned no rows for this chart, so there is nothing to interpret.";
  }

  if (chart.chart_type === "correlation_heatmap") {
    const strongest = chart.chart_data
      .filter((row) => row.metric_x !== row.metric_y)
      .map((row) => ({
        x: String(row.metric_x),
        y: String(row.metric_y),
        value: Number(row.correlation)
      }))
      .filter((row) => Number.isFinite(row.value))
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))[0];

    if (!strongest) {
      return "The heatmap shows pairwise metric correlations returned by the backend.";
    }

    return `The strongest non-self relationship shown is ${strongest.x} vs ${strongest.y} at ${strongest.value.toFixed(2)} correlation.`;
  }

  if (chart.chart_type === "scatter") {
    return `This exhibit plots ${chart.chart_data.length.toLocaleString()} backend-provided points to show row-level relationship between ${chart.x_column} and ${chart.y_column}.`;
  }

  const valueKey = chart.chart_type === "horizontal_bar" ? chart.x_column : chart.y_column;
  const labelKey = chart.chart_type === "horizontal_bar" ? chart.y_column : chart.x_column;
  if (!valueKey || !labelKey) {
    return "This chart uses backend-provided rows for an analytical exhibit.";
  }

  const ranked = chart.chart_data
    .map((row) => ({
      label: String(row[labelKey] ?? "Unknown"),
      value: Number(row[valueKey])
    }))
    .filter((row) => Number.isFinite(row.value))
    .sort((a, b) => b.value - a.value);

  const top = ranked[0];
  const bottom = ranked[ranked.length - 1];
  if (!top || !bottom) {
    return "This chart uses backend-provided rows for an analytical exhibit.";
  }

  if (chart.chart_type === "line") {
    return `The series spans ${chart.chart_data.length.toLocaleString()} time points. The highest plotted value is ${formatCompact(top.value)}.`;
  }

  if (chart.chart_type === "histogram") {
    return `The most populated bin is ${top.label} with ${formatCompact(top.value)} records.`;
  }

  return `${top.label} is the highest plotted category at ${formatCompact(top.value)}; ${bottom.label} is the lowest at ${formatCompact(bottom.value)}.`;
}

function formatCompact(value: number) {
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${(value / 1_000).toFixed(1)}k`;
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function hasUsableChartData(chart: ChartSpec) {
  if (!chart.chart_data.length) {
    return false;
  }

  const numericValues = chart.chart_data
    .flatMap((row) => Object.values(row))
    .map((value) => (typeof value === "number" ? value : Number(value)))
    .filter((value) => Number.isFinite(value));

  if (!numericValues.length) {
    return false;
  }

  if (chart.chart_type === "correlation_heatmap") {
    return chart.chart_data.some((row) => Number.isFinite(Number(row.correlation)));
  }

  return new Set(numericValues).size > 1;
}

function ChartFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-surface-raised px-3 py-2">
      <p className="text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 truncate text-body-sm text-foreground">{value}</p>
    </div>
  );
}
