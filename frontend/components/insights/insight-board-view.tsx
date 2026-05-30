"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  BarChart3,
  ChevronRight,
  Columns3,
  FileText,
  FileSearch,
  Lightbulb,
  ShieldAlert,
  Target,
  X
} from "lucide-react";
import { EvidenceBadge } from "@/components/insights/evidence-badge";
import { InsightSeverityBadge } from "@/components/insights/insight-severity-badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { Panel } from "@/components/ui/panel";
import { SectionLabel } from "@/components/ui/section-label";
import { StatusBadge } from "@/components/ui/status-badge";
import { apiGet, normalizeUnknownError, type ApiClientError } from "@/lib/api-client";
import type { ChartSpec, Evidence, Insight } from "@/types/api";
import { cn } from "@/lib/utils";

type InsightBoardViewProps = {
  datasetId: string;
};

type InsightGroupKey = "key_findings" | "risks" | "opportunities" | "data_quality";

type InsightGroup = {
  key: InsightGroupKey;
  title: string;
  description: string;
  icon: ReactNode;
  insights: Insight[];
};

export function InsightBoardView({ datasetId }: InsightBoardViewProps) {
  const [insights, setInsights] = useState<Insight[] | null>(null);
  const [charts, setCharts] = useState<ChartSpec[]>([]);
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null);
  const [error, setError] = useState<ApiClientError | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadInsights() {
      try {
        const [insightResponse, chartResponse] = await Promise.all([
          apiGet<Insight[]>(`/api/datasets/${encodeURIComponent(datasetId)}/insights`),
          apiGet<ChartSpec[]>(`/api/datasets/${encodeURIComponent(datasetId)}/charts`)
        ]);

        if (!cancelled) {
          setInsights(insightResponse);
          setCharts(chartResponse);
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(normalizeUnknownError(caughtError));
        }
      }
    }

    void loadInsights();

    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  const chartById = useMemo(
    () => new Map(charts.map((chart) => [chart.id, chart])),
    [charts]
  );

  const groups = useMemo(() => groupInsights(insights ?? []), [insights]);
  const severityCounts = useMemo(() => countSeverities(insights ?? []), [insights]);

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

  if (!insights) {
    return (
      <LoadingState
        title="Generating insights"
        description="Running deterministic rules and attaching evidence to each finding."
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
          <StatusBadge tone="danger">{`${severityCounts.high} high`}</StatusBadge>
          <StatusBadge tone="warning">{`${severityCounts.medium} medium`}</StatusBadge>
          <StatusBadge>{`${insights.length} insights`}</StatusBadge>
          <Button asChild size="sm">
            <Link href={`/studio/datasets/${datasetId}/report`}>
              <FileText className="mr-2 h-4 w-4" aria-hidden="true" />
              Generate Report
            </Link>
          </Button>
        </div>
      </div>

      {insights.length === 0 ? (
        <EmptyState
          title="No material insights crossed threshold"
          description="The backend did not find strong enough deterministic evidence to generate insight cards for this dataset."
          icon={<Lightbulb className="h-4 w-4" aria-hidden="true" />}
        />
      ) : (
        <div className="space-y-6">
          <BriefingHeader insights={insights} />
          {groups.map((group) => (
            <InsightGroupSection
              key={group.key}
              group={group}
              chartById={chartById}
              onOpenEvidence={setSelectedInsight}
            />
          ))}
        </div>
      )}

      <EvidenceDrawer
        insight={selectedInsight}
        relatedChart={selectedInsight?.related_chart_id ? chartById.get(selectedInsight.related_chart_id) : undefined}
        onClose={() => setSelectedInsight(null)}
      />
    </div>
  );
}

function BriefingHeader({ insights }: { insights: Insight[] }) {
  const topInsight = [...insights].sort((a, b) => {
    const severityRank = severityWeight(b.severity) - severityWeight(a.severity);
    if (severityRank !== 0) {
      return severityRank;
    }
    return b.confidence - a.confidence;
  })[0];

  return (
    <Panel className="overflow-hidden">
      <div className="grid gap-0 lg:grid-cols-[280px_minmax(0,1fr)]">
        <div className="bg-surface-inverse p-6 text-primary-foreground">
          <p className="text-caption font-medium uppercase tracking-[0.16em] text-primary-foreground/60">
            Analyst briefing
          </p>
          <p className="mt-5 text-display-md font-semibold">{insights.length}</p>
          <p className="mt-2 text-body-sm text-primary-foreground/70">
            deterministic insights generated from backend evidence.
          </p>
        </div>
        <div className="p-6">
          <SectionLabel
            eyebrow="Highest priority"
            title={topInsight?.title ?? "No insight selected"}
            description={topInsight?.summary ?? "Insight cards appear here after deterministic thresholds are met."}
            action={topInsight ? <InsightSeverityBadge severity={topInsight.severity} /> : null}
          />
          {topInsight?.recommendation ? (
            <p className="mt-5 rounded-lg border bg-surface-raised px-4 py-3 text-body-sm text-muted-foreground">
              <span className="font-semibold text-foreground">Recommended action:</span>{" "}
              {topInsight.recommendation}
            </p>
          ) : null}
        </div>
      </div>
    </Panel>
  );
}

function InsightGroupSection({
  group,
  chartById,
  onOpenEvidence
}: {
  group: InsightGroup;
  chartById: Map<string, ChartSpec>;
  onOpenEvidence: (insight: Insight) => void;
}) {
  if (group.insights.length === 0) {
    return null;
  }

  return (
    <section className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="mt-1 flex h-9 w-9 items-center justify-center rounded-md border bg-surface text-muted-foreground">
            {group.icon}
          </span>
          <div>
            <h2 className="text-heading-sm font-semibold text-foreground">{group.title}</h2>
            <p className="mt-1 text-body-sm text-muted-foreground">{group.description}</p>
          </div>
        </div>
        <StatusBadge>{`${group.insights.length}`}</StatusBadge>
      </div>

      <div className="grid gap-4">
        {group.insights.map((insight) => (
          <InsightBriefingCard
            key={insight.id}
            insight={insight}
            relatedChart={insight.related_chart_id ? chartById.get(insight.related_chart_id) : undefined}
            onOpenEvidence={() => onOpenEvidence(insight)}
          />
        ))}
      </div>
    </section>
  );
}

function InsightBriefingCard({
  insight,
  relatedChart,
  onOpenEvidence
}: {
  insight: Insight;
  relatedChart?: ChartSpec;
  onOpenEvidence: () => void;
}) {
  return (
    <Panel
      as="article"
      className={cn(
        "overflow-hidden transition-shadow hover:shadow-panel-hover",
        insight.severity === "high" && "border-red-200",
        insight.severity === "medium" && "border-amber-200"
      )}
    >
      <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_260px]">
        <div className="p-5">
          <div className="flex flex-wrap items-center gap-2">
            <InsightSeverityBadge severity={insight.severity} />
            <StatusBadge>{`${Math.round(insight.confidence * 100)}% confidence`}</StatusBadge>
            <EvidenceBadge label="Evidence available" />
          </div>
          <h3 className="mt-5 text-heading-sm font-semibold text-foreground">{insight.title}</h3>
          <p className="mt-3 text-body-sm text-muted-foreground">{insight.summary}</p>

          {insight.recommendation ? (
            <div className="mt-5 rounded-lg border bg-surface-raised px-4 py-3">
              <p className="text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
                Recommendation
              </p>
              <p className="mt-2 text-body-sm text-foreground">{insight.recommendation}</p>
            </div>
          ) : null}
        </div>
        <aside className="border-t bg-surface-raised p-5 lg:border-l lg:border-t-0">
          <p className="text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
            Related columns
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {insight.related_columns.length > 0 ? (
              insight.related_columns.map((column) => (
                <span
                  key={column}
                  className="inline-flex h-6 items-center rounded-full border bg-surface px-2.5 text-caption text-muted-foreground"
                >
                  {column}
                </span>
              ))
            ) : (
              <span className="text-body-sm text-muted-foreground">None specified</span>
            )}
          </div>

          {relatedChart ? (
            <div className="mt-5 rounded-md border bg-surface px-3 py-2">
              <p className="flex items-center gap-2 text-caption font-medium text-muted-foreground">
                <BarChart3 className="h-3.5 w-3.5" aria-hidden="true" />
                Related chart
              </p>
              <p className="mt-1 text-body-sm font-medium text-foreground">{relatedChart.title}</p>
            </div>
          ) : null}

          <Button type="button" variant="outline" className="mt-5 w-full" onClick={onOpenEvidence}>
            View evidence
            <ChevronRight className="ml-2 h-4 w-4" aria-hidden="true" />
          </Button>
        </aside>
      </div>
    </Panel>
  );
}

function EvidenceDrawer({
  insight,
  relatedChart,
  onClose
}: {
  insight: Insight | null;
  relatedChart?: ChartSpec;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {insight ? (
        <>
          <motion.button
            type="button"
            aria-label="Close evidence drawer"
            className="fixed inset-0 z-40 bg-graphite-950/20"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className="fixed bottom-0 right-0 top-0 z-50 flex w-full max-w-xl flex-col border-l bg-surface shadow-panel"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.22, ease: [0.2, 0, 0, 1] }}
            aria-label="Evidence drawer"
          >
            <div className="flex items-start justify-between gap-4 border-b px-6 py-5">
              <div>
                <p className="text-caption font-medium uppercase tracking-[0.16em] text-muted-foreground">
                  Evidence
                </p>
                <h2 className="mt-2 text-heading-sm font-semibold text-foreground">{insight.title}</h2>
              </div>
              <Button type="button" variant="quiet" size="icon" onClick={onClose} aria-label="Close evidence drawer">
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-5">
              <div className="mb-5 flex flex-wrap items-center gap-2">
                <InsightSeverityBadge severity={insight.severity} />
                <StatusBadge>{`${Math.round(insight.confidence * 100)}% confidence`}</StatusBadge>
                <StatusBadge>{insight.insight_type.replaceAll("_", " ")}</StatusBadge>
              </div>

              <EvidenceSection title="Calculation performed" value={insight.evidence.calculation} mono />
              <EvidenceSection title="Explanation" value={insight.evidence.explanation} />
              <EvidenceList title="Columns used" values={evidenceColumns(insight.evidence, insight.related_columns)} />
              <EvidenceObject title="Values" value={insight.evidence.values} fallback={insight.evidence.value} />
              <EvidenceObject
                title="Comparison values"
                value={insight.evidence.comparison_values}
                fallback={insight.evidence.comparison_value}
              />
              <EvidenceSection
                title="Rows affected"
                value={
                  insight.evidence.rows_affected !== null && insight.evidence.rows_affected !== undefined
                    ? insight.evidence.rows_affected.toLocaleString()
                    : "Not applicable to this calculation"
                }
              />

              {relatedChart ? (
                <div className="mt-5 rounded-lg border bg-surface-raised p-4">
                  <p className="flex items-center gap-2 text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
                    <BarChart3 className="h-3.5 w-3.5" aria-hidden="true" />
                    Related chart
                  </p>
                  <p className="mt-2 text-body-sm font-semibold text-foreground">{relatedChart.title}</p>
                  <p className="mt-2 text-body-sm text-muted-foreground">{relatedChart.description}</p>
                </div>
              ) : (
                <EvidenceSection title="Related chart" value="No related chart was attached to this insight." />
              )}
            </div>
          </motion.aside>
        </>
      ) : null}
    </AnimatePresence>
  );
}

function EvidenceSection({
  title,
  value,
  mono = false
}: {
  title: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <section className="mt-5 rounded-lg border bg-surface-raised p-4">
      <p className="text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
        {title}
      </p>
      <p className={cn("mt-2 text-body-sm text-foreground", mono && "font-mono text-caption leading-6")}>
        {value}
      </p>
    </section>
  );
}

function EvidenceList({ title, values }: { title: string; values: string[] }) {
  return (
    <section className="mt-5 rounded-lg border bg-surface-raised p-4">
      <p className="text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
        {title}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {values.length > 0 ? (
          values.map((value) => (
            <span key={value} className="inline-flex h-7 items-center rounded-full border bg-surface px-2.5 text-caption text-muted-foreground">
              {value}
            </span>
          ))
        ) : (
          <span className="text-body-sm text-muted-foreground">No columns specified</span>
        )}
      </div>
    </section>
  );
}

function EvidenceObject({
  title,
  value,
  fallback
}: {
  title: string;
  value: Record<string, unknown>;
  fallback?: unknown;
}) {
  const entries = Object.entries(value ?? {});
  const hasFallback = fallback !== null && fallback !== undefined;

  return (
    <section className="mt-5 rounded-lg border bg-surface-raised p-4">
      <p className="text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
        {title}
      </p>
      {entries.length > 0 ? (
        <div className="mt-3 divide-y rounded-md border bg-surface">
          {entries.map(([key, entryValue]) => (
            <div key={key} className="grid grid-cols-[140px_minmax(0,1fr)] gap-3 px-3 py-2 text-body-sm">
              <span className="text-muted-foreground">{key}</span>
              <span className="break-words font-medium text-foreground">{formatEvidenceValue(entryValue)}</span>
            </div>
          ))}
        </div>
      ) : hasFallback ? (
        <p className="mt-2 text-body-sm font-medium text-foreground">{formatEvidenceValue(fallback)}</p>
      ) : (
        <p className="mt-2 text-body-sm text-muted-foreground">Not provided for this evidence object.</p>
      )}
    </section>
  );
}

function groupInsights(insights: Insight[]): InsightGroup[] {
  const groups: Record<InsightGroupKey, Insight[]> = {
    key_findings: [],
    risks: [],
    opportunities: [],
    data_quality: []
  };

  insights.forEach((insight) => {
    groups[classifyInsight(insight)].push(insight);
  });

  return [
    {
      key: "key_findings",
      title: "Key Findings",
      description: "Material patterns and relationships supported by computed evidence.",
      icon: <FileSearch className="h-4 w-4" aria-hidden="true" />,
      insights: sortInsights(groups.key_findings)
    },
    {
      key: "risks",
      title: "Risks",
      description: "Findings that may affect confidence, concentration, or operational exposure.",
      icon: <ShieldAlert className="h-4 w-4" aria-hidden="true" />,
      insights: sortInsights(groups.risks)
    },
    {
      key: "opportunities",
      title: "Opportunities",
      description: "Lower-risk findings with practical follow-up actions.",
      icon: <Target className="h-4 w-4" aria-hidden="true" />,
      insights: sortInsights(groups.opportunities)
    },
    {
      key: "data_quality",
      title: "Data Quality",
      description: "Evidence about missingness, duplicates, and suspicious structure.",
      icon: <Columns3 className="h-4 w-4" aria-hidden="true" />,
      insights: sortInsights(groups.data_quality)
    }
  ];
}

function classifyInsight(insight: Insight): InsightGroupKey {
  if (
    insight.insight_type === "dataset_quality" ||
    insight.insight_type === "missing_data_risk"
  ) {
    return "data_quality";
  }

  if (
    insight.severity === "high" ||
    insight.insight_type === "outlier" ||
    insight.insight_type === "concentration"
  ) {
    return "risks";
  }

  if (insight.severity === "low" && Boolean(insight.recommendation)) {
    return "opportunities";
  }

  return "key_findings";
}

function sortInsights(insights: Insight[]) {
  return [...insights].sort((a, b) => {
    const severityDelta = severityWeight(b.severity) - severityWeight(a.severity);
    if (severityDelta !== 0) {
      return severityDelta;
    }
    return b.confidence - a.confidence;
  });
}

function severityWeight(severity: Insight["severity"]) {
  if (severity === "high") {
    return 3;
  }
  if (severity === "medium") {
    return 2;
  }
  return 1;
}

function countSeverities(insights: Insight[]) {
  return insights.reduce(
    (counts, insight) => {
      counts[insight.severity] += 1;
      return counts;
    },
    { high: 0, medium: 0, low: 0 }
  );
}

function evidenceColumns(evidence: Evidence, relatedColumns: string[]) {
  return Array.from(new Set([...(evidence.columns ?? []), evidence.column, ...relatedColumns].filter(Boolean))) as string[];
}

function formatEvidenceValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "Not provided";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 3 });
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
