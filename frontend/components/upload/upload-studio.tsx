"use client";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Database,
  FileSpreadsheet,
  Loader2,
  UploadCloud
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Panel } from "@/components/ui/panel";
import { SectionLabel } from "@/components/ui/section-label";
import { StatusBadge } from "@/components/ui/status-badge";
import { DataPreviewTable } from "@/components/upload/data-preview-table";
import {
  ACCEPTED_MIME_TYPES,
  getDatasetPreview,
  getSampleDatasetFile,
  uploadDataset,
  validateDatasetFile,
  type UploadProgressState
} from "@/lib/dataset-api";
import { ApiClientError, normalizeUnknownError } from "@/lib/api-client";
import type { DatasetPreviewResponse, DatasetUploadResponse } from "@/types/api";
import { cn } from "@/lib/utils";

type UploadStatus = "idle" | "uploading" | "parsing" | "success" | "error";

export function UploadStudio() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<DatasetUploadResponse | null>(null);
  const [preview, setPreview] = useState<DatasetPreviewResponse | null>(null);
  const [error, setError] = useState<ApiClientError | null>(null);

  const isBusy = status === "uploading" || status === "parsing";

  const handleFile = useCallback(async (file: File) => {
    const validationError = validateDatasetFile(file);
    setSelectedFileName(file.name);
    setUploadResult(null);
    setPreview(null);

    if (validationError) {
      setStatus("error");
      setError(
        new ApiClientError({
          code: "INVALID_UPLOAD_FILE",
          message: validationError,
          suggestedFix: "Choose a non-empty CSV or XLSX file under 25 MB."
        })
      );
      return;
    }

    try {
      setError(null);
      setProgress(0);
      setStatus("uploading");

      const uploaded = await uploadDataset(file, (nextProgress, phase: UploadProgressState) => {
        setProgress(nextProgress);
        setStatus(phase);
      });

      setUploadResult(uploaded);
      setStatus("parsing");

      const previewResponse = await getDatasetPreview(uploaded.dataset_id, 20);
      setPreview(previewResponse);
      setProgress(100);
      setStatus("success");
    } catch (caughtError) {
      setStatus("error");
      setError(normalizeUnknownError(caughtError));
      setProgress(0);
    }
  }, []);

  const handleSampleDataset = async () => {
    try {
      setStatus("parsing");
      setError(null);
      setProgress(0);
      const sampleFile = await getSampleDatasetFile();
      await handleFile(sampleFile);
    } catch (caughtError) {
      setStatus("error");
      setError(normalizeUnknownError(caughtError));
    }
  };

  return (
    <div className="space-y-6">
      <Panel id="ingest" className="overflow-hidden">
        <div className="border-b px-6 py-5">
          <SectionLabel
            eyebrow="Upload Studio"
            title="Start with a spreadsheet"
            description="Upload a CSV or XLSX file. InsightPilot will parse the file, preserve original column names, and return a real preview from the backend artifact."
            action={<StatusBadge tone={status === "success" ? "success" : "neutral"}>{statusLabel(status)}</StatusBadge>}
          />
        </div>

        <div className="grid gap-6 p-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED_MIME_TYPES}
              className="sr-only"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  void handleFile(file);
                }
                event.target.value = "";
              }}
            />

            <button
              type="button"
              disabled={isBusy}
              onClick={() => inputRef.current?.click()}
              onDragEnter={(event) => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragOver={(event) => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={(event) => {
                event.preventDefault();
                setDragActive(false);
              }}
              onDrop={(event) => {
                event.preventDefault();
                setDragActive(false);
                const file = event.dataTransfer.files?.[0];
                if (file) {
                  void handleFile(file);
                }
              }}
              className={cn(
                "flex min-h-80 w-full flex-col items-center justify-center rounded-lg border border-dashed bg-surface-raised px-6 py-10 text-center transition-all duration-150 ease-productive",
                "hover:border-foreground hover:bg-surface disabled:pointer-events-none disabled:opacity-70",
                dragActive && "border-accent bg-blue-50/50"
              )}
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-md border bg-surface text-muted-foreground shadow-hairline">
                {isBusy ? (
                  <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                ) : status === "success" ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden="true" />
                ) : (
                  <UploadCloud className="h-5 w-5" aria-hidden="true" />
                )}
              </span>
              <h2 className="mt-5 text-heading-sm font-semibold text-foreground">
                {isBusy ? "Uploading and parsing your dataset" : "Drop a spreadsheet here"}
              </h2>
              <p className="mt-2 max-w-md text-body-sm text-muted-foreground">
                CSV and XLSX files are supported up to 25 MB for the local MVP.
              </p>
              {selectedFileName ? (
                <p className="mt-4 rounded-full border bg-surface px-3 py-1 text-caption text-muted-foreground">
                  {selectedFileName}
                </p>
              ) : null}
              {isBusy ? <ProgressBar progress={progress} status={status} /> : null}
            </button>
          </div>

          <aside className="rounded-lg border bg-surface-raised p-5">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <h3 className="text-body-sm font-semibold text-foreground">Try the sample</h3>
            </div>
            <p className="mt-3 text-body-sm text-muted-foreground">
              Use the bundled SaaS growth CSV to explore profiling, chart recommendations,
              evidence-backed insights, and report export without preparing your own file.
            </p>
            <Button
              type="button"
              variant="outline"
              className="mt-5 w-full"
              disabled={isBusy}
              onClick={() => void handleSampleDataset()}
            >
              <FileSpreadsheet className="mr-2 h-4 w-4" aria-hidden="true" />
              Choose sample dataset
            </Button>
            <div className="mt-5 space-y-3 border-t pt-5 text-caption text-muted-foreground">
              <p>Accepted: `.csv`, `.xlsx`</p>
              <p>Limit: 25 MB</p>
              <p>Preview: first 20 parsed rows</p>
            </div>
          </aside>
        </div>
      </Panel>

      {status === "error" && error ? (
        <ErrorState
          title={error.message}
          description={error.suggestedFix ?? "Check the file format, confirm the backend is running, and try again."}
          detail={error.technicalDetail ?? error.code}
          action={
            <Button type="button" variant="outline" onClick={() => inputRef.current?.click()}>
              Select another file
            </Button>
          }
        />
      ) : null}

      {status === "success" && uploadResult ? (
        <SuccessPreview uploadResult={uploadResult} preview={preview} />
      ) : null}

      {status === "idle" ? (
        <EmptyState
          title="No dataset loaded"
          description="Once a file is parsed, InsightPilot will show a file summary, parser warnings, and a preview table from the backend."
          icon={<AlertCircle className="h-4 w-4" aria-hidden="true" />}
        />
      ) : null}
    </div>
  );
}

function ProgressBar({ progress, status }: { progress: number; status: UploadStatus }) {
  return (
    <div className="mt-6 w-full max-w-md">
      <div className="flex items-center justify-between text-caption text-muted-foreground">
        <span>{status === "parsing" ? "Parsing dataset" : "Uploading file"}</span>
        <span>{progress}%</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full rounded-full bg-accent transition-all duration-200"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

function SuccessPreview({
  uploadResult,
  preview
}: {
  uploadResult: DatasetUploadResponse;
  preview: DatasetPreviewResponse | null;
}) {
  const rows = preview?.preview_rows ?? uploadResult.preview_rows;
  const columns = preview?.columns ?? uploadResult.columns;

  return (
    <Panel className="overflow-hidden">
      <div className="border-b px-6 py-5">
        <SectionLabel
          eyebrow="Parsed dataset"
          title={uploadResult.filename}
          description="The backend accepted the file and returned parsed metadata plus preview rows."
          action={
            <Button asChild>
              <Link href={`/studio/datasets/${uploadResult.dataset_id}/profile`}>
                Continue to Dataset Profile
                <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
          }
        />
      </div>
      <div className="grid gap-4 border-b bg-surface-raised p-6 sm:grid-cols-3">
        <SummaryStat label="Rows" value={uploadResult.row_count.toLocaleString()} />
        <SummaryStat label="Columns" value={uploadResult.column_count.toLocaleString()} />
        <SummaryStat label="Warnings" value={uploadResult.warnings.length.toLocaleString()} />
      </div>
      {uploadResult.warnings.length > 0 ? (
        <div className="border-b px-6 py-4">
          <div className="space-y-2">
            {uploadResult.warnings.map((warning) => (
              <p key={`${warning.code}-${warning.message}`} className="text-body-sm text-muted-foreground">
                <span className="font-medium text-foreground">{warning.code}:</span> {warning.message}
              </p>
            ))}
          </div>
        </div>
      ) : null}
      <div className="p-6">
        <SectionLabel
          title="Data preview"
          description={`Showing ${rows.length} rows from the parsed dataset artifact.`}
        />
        <div className="mt-5">
          <DataPreviewTable columns={columns} rows={rows} />
        </div>
      </div>
    </Panel>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-surface px-4 py-3 shadow-panel">
      <p className="text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 text-heading-md font-semibold text-foreground">{value}</p>
    </div>
  );
}

function statusLabel(status: UploadStatus) {
  if (status === "uploading") {
    return "Uploading";
  }
  if (status === "parsing") {
    return "Parsing";
  }
  if (status === "success") {
    return "Parsed";
  }
  if (status === "error") {
    return "Needs attention";
  }
  return "Ready";
}
