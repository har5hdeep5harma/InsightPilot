"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  FileWarning,
  Fingerprint,
  ListChecks,
  TableProperties
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { Panel } from "@/components/ui/panel";
import { SectionLabel } from "@/components/ui/section-label";
import { StatusBadge } from "@/components/ui/status-badge";
import { apiGet, normalizeUnknownError, type ApiClientError } from "@/lib/api-client";
import type {
  AnalysisWarning,
  ColumnProfile,
  DatasetDetailResponse,
  DatasetProfile
} from "@/types/api";
import { cn } from "@/lib/utils";

type DatasetProfileViewProps = {
  datasetId: string;
};

type ProfileState = {
  profile: DatasetProfile;
  dataset: DatasetDetailResponse | null;
};

export function DatasetProfileView({ datasetId }: DatasetProfileViewProps) {
  const [state, setState] = useState<ProfileState | null>(null);
  const [error, setError] = useState<ApiClientError | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadProfile() {
      try {
        const [profile, dataset] = await Promise.all([
          apiGet<DatasetProfile>(`/api/datasets/${encodeURIComponent(datasetId)}/profile`),
          apiGet<DatasetDetailResponse>(`/api/datasets/${encodeURIComponent(datasetId)}`)
        ]);

        if (!cancelled) {
          setState({ profile, dataset });
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(normalizeUnknownError(caughtError));
        }
      }
    }

    void loadProfile();

    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  if (error) {
    return (
      <ErrorState
        title={error.message}
        description={error.suggestedFix ?? "Return to the upload studio and try another dataset."}
        detail={error.technicalDetail ?? error.code}
        action={
          <Button asChild variant="outline">
            <Link href="/studio">Back to Upload Studio</Link>
          </Button>
        }
      />
    );
  }

  if (!state) {
    return (
      <LoadingState
        title="Profiling dataset"
        description="Computing column roles, quality checks, duplicate rows, and summary statistics."
      />
    );
  }

  const { profile, dataset } = state;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button asChild variant="quiet" size="sm">
          <Link href="/studio">
            <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
            Back to upload
          </Link>
        </Button>
        <div className="flex flex-wrap items-center gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href={`/studio/datasets/${datasetId}/charts`}>
              Chart Gallery
              <BarChart3 className="ml-2 h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
          <Button asChild size="sm">
            <Link href={`/studio/datasets/${datasetId}/insights`}>
              Generate insights
              <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </div>

      <DatasetOverview profile={profile} filename={dataset?.original_filename ?? dataset?.filename} />
      <DetectedRoles profile={profile} />
      <DataQualityPanel profile={profile} parsingWarnings={dataset?.warnings ?? []} />
      <ColumnProfileTable columns={profile.columns} />
    </div>
  );
}

function DatasetOverview({
  profile,
  filename
}: {
  profile: DatasetProfile;
  filename?: string;
}) {
  return (
    <Panel className="overflow-hidden">
      <div className="grid gap-0 lg:grid-cols-[280px_minmax(0,1fr)]">
        <div className="border-b bg-surface-inverse p-6 text-primary-foreground lg:border-b-0 lg:border-r">
          <p className="text-caption font-medium uppercase tracking-[0.16em] text-primary-foreground/60">
            Quality score
          </p>
          <div className="mt-6 flex items-end gap-3">
            <span className="text-display-md font-semibold">{Math.round(profile.quality_score)}</span>
            <span className="mb-2 text-body-sm text-primary-foreground/60">/ 100</span>
          </div>
          <div className="mt-5 h-2 overflow-hidden rounded-full bg-white/15">
            <div
              className="h-full rounded-full bg-white transition-all"
              style={{ width: `${Math.max(0, Math.min(profile.quality_score, 100))}%` }}
            />
          </div>
          <p className="mt-5 text-body-sm text-primary-foreground/70">
            {qualityCopy(profile.quality_score)}
          </p>
        </div>
        <div className="p-6">
          <SectionLabel
            eyebrow="Dataset overview"
            title={filename ?? "Uploaded dataset"}
            description="InsightPilot profiles the parsed artifact before recommending charts or generating insights."
          />
          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <ProfileStat label="Rows" value={profile.row_count.toLocaleString()} />
            <ProfileStat label="Columns" value={profile.column_count.toLocaleString()} />
            <ProfileStat label="Duplicate rows" value={profile.duplicate_row_count.toLocaleString()} />
            <ProfileStat label="Memory" value={formatBytes(profile.memory_usage)} />
          </div>
        </div>
      </div>
    </Panel>
  );
}

function DetectedRoles({ profile }: { profile: DatasetProfile }) {
  const roleGroups = [
    { label: "Metrics", columns: profile.numeric_columns, tone: "metric" },
    { label: "Dimensions", columns: profile.categorical_columns, tone: "dimension" },
    { label: "Datetime", columns: profile.datetime_columns, tone: "datetime" },
    { label: "ID-like", columns: profile.id_like_columns, tone: "id" },
    { label: "Text", columns: profile.text_columns, tone: "text" }
  ];

  return (
    <Panel className="p-6">
      <SectionLabel
        eyebrow="Detected column roles"
        title="What InsightPilot understood"
        description="Column roles are inferred from parsed values, uniqueness, missingness, and type patterns."
      />
      <div className="mt-6 grid gap-4 lg:grid-cols-5">
        {roleGroups.map((group) => (
          <div key={group.label} className="rounded-lg border bg-surface-raised p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-body-sm font-semibold text-foreground">{group.label}</h3>
              <StatusBadge>{String(group.columns.length)}</StatusBadge>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {group.columns.length > 0 ? (
                group.columns.map((column) => (
                  <RoleBadge key={column} role={group.tone}>
                    {column}
                  </RoleBadge>
                ))
              ) : (
                <p className="text-body-sm text-muted-foreground">None detected</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function DataQualityPanel({
  profile,
  parsingWarnings
}: {
  profile: DatasetProfile;
  parsingWarnings: AnalysisWarning[];
}) {
  const missingColumns = profile.columns.filter((column) => column.missing_count > 0);
  const highCardinality = profile.columns.filter(
    (column) =>
      column.unique_percentage >= 80 ||
      column.warnings.some((warning) => warning.code.toLowerCase().includes("cardinality"))
  );
  const suspiciousColumns = profile.columns.filter(
    (column) =>
      column.role === "ignored" ||
      column.inferred_type === "unknown" ||
      column.warnings.some((warning) =>
        ["suspicious", "stored_as_text", "date", "skew"].some((token) =>
          `${warning.code} ${warning.message}`.toLowerCase().includes(token)
        )
      )
  );

  return (
    <Panel className="p-6">
      <SectionLabel
        eyebrow="Data quality"
        title="Quality checks without drama"
        description="Warnings are presented as review notes. They do not block analysis unless the backend rejects the file."
      />
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <QualityCard
          icon={<ListChecks className="h-4 w-4" aria-hidden="true" />}
          title="Missing values"
          summary={
            missingColumns.length === 0
              ? "No missing values detected in profiled columns."
              : `${missingColumns.length} columns contain missing values.`
          }
          items={missingColumns
            .sort((a, b) => b.missing_percentage - a.missing_percentage)
            .slice(0, 5)
            .map((column) => `${column.original_name}: ${column.missing_percentage.toFixed(1)}% missing`)}
        />
        <QualityCard
          icon={<Fingerprint className="h-4 w-4" aria-hidden="true" />}
          title="Duplicate rows"
          summary={
            profile.duplicate_row_count === 0
              ? "No duplicate rows detected."
              : `${profile.duplicate_row_count.toLocaleString()} duplicate rows detected.`
          }
          items={profile.duplicate_row_count > 0 ? ["Review duplicates before drawing final conclusions."] : []}
        />
        <QualityCard
          icon={<TableProperties className="h-4 w-4" aria-hidden="true" />}
          title="High-cardinality columns"
          summary={
            highCardinality.length === 0
              ? "No high-cardinality review notes."
              : `${highCardinality.length} columns may be too granular for grouping.`
          }
          items={highCardinality.slice(0, 5).map((column) => `${column.original_name}: ${column.unique_percentage.toFixed(1)}% unique`)}
        />
        <QualityCard
          icon={<FileWarning className="h-4 w-4" aria-hidden="true" />}
          title="Suspicious and parsing warnings"
          summary={
            suspiciousColumns.length + parsingWarnings.length === 0
              ? "No suspicious column or parser warnings detected."
              : `${suspiciousColumns.length + parsingWarnings.length} review notes found.`
          }
          items={[
            ...suspiciousColumns.slice(0, 4).map((column) => `${column.original_name}: ${summarizeWarnings(column.warnings)}`),
            ...parsingWarnings.slice(0, 4).map((warning) => `Parser: ${warning.message}`)
          ]}
        />
      </div>
      {profile.warnings.length > 0 ? (
        <div className="mt-5 rounded-lg border bg-surface-raised p-4">
          <p className="text-body-sm font-semibold text-foreground">Dataset-level notes</p>
          <div className="mt-3 space-y-2">
            {profile.warnings.map((warning) => (
              <WarningLine key={`${warning.code}-${warning.message}`} warning={warning} />
            ))}
          </div>
        </div>
      ) : null}
    </Panel>
  );
}

function ColumnProfileTable({ columns }: { columns: ColumnProfile[] }) {
  return (
    <Panel className="overflow-hidden">
      <div className="border-b px-6 py-5">
        <SectionLabel
          eyebrow="Column profile table"
          title="Column-by-column understanding"
          description="Each row reflects computed profile data from the backend response."
        />
      </div>
      <div className="overflow-auto">
        <table className="w-full min-w-[1080px] text-left text-body-sm">
          <thead className="bg-surface-raised text-muted-foreground">
            <tr>
              <th className="border-b px-4 py-3 font-medium">Name</th>
              <th className="border-b px-4 py-3 font-medium">Inferred type</th>
              <th className="border-b px-4 py-3 font-medium">Role</th>
              <th className="border-b px-4 py-3 font-medium">Missing %</th>
              <th className="border-b px-4 py-3 font-medium">Unique %</th>
              <th className="border-b px-4 py-3 font-medium">Sample values</th>
              <th className="border-b px-4 py-3 font-medium">Warnings</th>
            </tr>
          </thead>
          <tbody>
            {columns.map((column) => (
              <tr key={column.name} className="border-b last:border-b-0">
                <td className="px-4 py-3 font-medium text-foreground">{column.original_name || column.name}</td>
                <td className="px-4 py-3 text-muted-foreground">{column.inferred_type}</td>
                <td className="px-4 py-3">
                  <RoleBadge role={column.role}>{column.role}</RoleBadge>
                </td>
                <td className="px-4 py-3 text-muted-foreground">{column.missing_percentage.toFixed(1)}%</td>
                <td className="px-4 py-3 text-muted-foreground">{column.unique_percentage.toFixed(1)}%</td>
                <td className="max-w-72 px-4 py-3 text-muted-foreground">
                  <span className="line-clamp-2">{formatSampleValues(column.sample_values)}</span>
                </td>
                <td className="max-w-80 px-4 py-3">
                  {column.warnings.length > 0 ? (
                    <div className="space-y-1">
                      {column.warnings.slice(0, 2).map((warning) => (
                        <WarningLine key={`${column.name}-${warning.code}-${warning.message}`} warning={warning} compact />
                      ))}
                    </div>
                  ) : (
                    <span className="text-muted-foreground">None</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function QualityCard({
  icon,
  title,
  summary,
  items
}: {
  icon: ReactNode;
  title: string;
  summary: string;
  items: string[];
}) {
  return (
    <div className="rounded-lg border bg-surface-raised p-4">
      <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-md border bg-surface text-muted-foreground">
          {icon}
        </span>
        <h3 className="text-body-sm font-semibold text-foreground">{title}</h3>
      </div>
      <p className="mt-3 text-body-sm text-muted-foreground">{summary}</p>
      {items.length > 0 ? (
        <ul className="mt-4 space-y-2">
          {items.map((item) => (
            <li key={item} className="rounded-md border bg-surface px-3 py-2 text-caption text-muted-foreground">
              {item}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function RoleBadge({ role, children }: { role: string; children: ReactNode }) {
  const normalizedRole = role.toLowerCase();
  const styles =
    normalizedRole === "metric"
      ? "border-blue-200 bg-blue-50 text-blue-700"
      : normalizedRole === "dimension"
        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
        : normalizedRole === "datetime"
          ? "border-violet-200 bg-violet-50 text-violet-700"
          : normalizedRole === "id"
            ? "border-slate-200 bg-slate-50 text-slate-700"
            : normalizedRole === "text"
              ? "border-amber-200 bg-amber-50 text-amber-700"
              : "border-border bg-secondary text-muted-foreground";

  return (
    <span className={cn("inline-flex h-6 items-center rounded-full border px-2.5 text-caption font-medium", styles)}>
      {children}
    </span>
  );
}

function WarningLine({ warning, compact = false }: { warning: AnalysisWarning; compact?: boolean }) {
  return (
    <p className={cn("text-muted-foreground", compact ? "text-caption" : "text-body-sm")}>
      <span className="font-medium text-foreground">{warning.code}:</span> {warning.message}
    </p>
  );
}

function ProfileStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-surface px-4 py-3 shadow-panel">
      <p className="text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 text-heading-md font-semibold text-foreground">{value}</p>
    </div>
  );
}

function qualityCopy(score: number) {
  if (score >= 90) {
    return "The dataset looks clean enough for the next analysis step.";
  }
  if (score >= 75) {
    return "The dataset is usable, with a few quality notes worth reviewing.";
  }
  return "The dataset needs review before relying on downstream conclusions.";
}

function formatBytes(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatSampleValues(values: unknown[]) {
  if (values.length === 0) {
    return "No sample values";
  }
  return values.map((value) => (value === null || value === undefined ? "null" : String(value))).join(", ");
}

function summarizeWarnings(warnings: AnalysisWarning[]) {
  if (warnings.length === 0) {
    return "Review suggested by inferred role or type.";
  }
  return warnings.map((warning) => warning.message).join(" ");
}
