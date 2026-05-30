import { API_BASE_URL, ApiClientError, apiGet } from "@/lib/api-client";
import type { ApiErrorEnvelope, DatasetPreviewResponse, DatasetUploadResponse } from "@/types/api";

export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
export const ACCEPTED_EXTENSIONS = [".csv", ".xlsx"];
export const ACCEPTED_MIME_TYPES =
  ".csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,.xlsx";

export type UploadProgressState = "uploading" | "parsing";

export function validateDatasetFile(file: File): string | null {
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();

  if (!ACCEPTED_EXTENSIONS.includes(extension)) {
    return "Upload a CSV or XLSX file. Other spreadsheet formats are not supported in the MVP.";
  }

  if (file.size === 0) {
    return "This file is empty. Export a spreadsheet with headers and at least one data row.";
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    return "This file is above the 25 MB local MVP limit. Try a smaller extract for analysis.";
  }

  return null;
}

export function uploadDataset(
  file: File,
  onProgress: (progress: number, state: UploadProgressState) => void
): Promise<DatasetUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.open("POST", `${API_BASE_URL}/api/datasets/upload`);
    xhr.responseType = "json";
    xhr.setRequestHeader("Accept", "application/json");

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) {
        onProgress(35, "uploading");
        return;
      }

      const progress = Math.round((event.loaded / event.total) * 85);
      onProgress(Math.max(8, Math.min(progress, 85)), "uploading");
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress(100, "parsing");
        resolve(xhr.response as DatasetUploadResponse);
        return;
      }

      const envelope = xhr.response as Partial<ApiErrorEnvelope> | null;
      if (envelope?.error) {
        reject(
          new ApiClientError({
            code: envelope.error.code,
            message: envelope.error.message,
            technicalDetail: envelope.error.technical_detail,
            suggestedFix: envelope.error.suggested_fix,
            details: envelope.error.details,
            status: xhr.status
          })
        );
        return;
      }

      reject(
        new ApiClientError({
          code: "UPLOAD_FAILED",
          message: `Upload failed with status ${xhr.status}.`,
          status: xhr.status
        })
      );
    };

    xhr.onerror = () => {
      reject(
        new ApiClientError({
          code: "NETWORK_ERROR",
          message: "Could not reach the InsightPilot backend.",
          suggestedFix: "Start the FastAPI backend on port 8000 and try again."
        })
      );
    };

    onProgress(5, "uploading");
    xhr.send(formData);
  });
}

export async function getDatasetPreview(datasetId: string, limit = 20) {
  return apiGet<DatasetPreviewResponse>(
    `/api/datasets/${encodeURIComponent(datasetId)}/preview?limit=${limit}`
  );
}

export async function getSampleDatasetFile(): Promise<File> {
  const response = await fetch("/sample-data/saas_growth_sample.csv");
  if (!response.ok) {
    throw new ApiClientError({
      code: "SAMPLE_DATASET_UNAVAILABLE",
      message: "The SaaS growth sample dataset could not be loaded.",
      suggestedFix: "Confirm the frontend public sample file exists and refresh the page."
    });
  }

  const blob = await response.blob();
  return new File([blob], "saas_growth_sample.csv", { type: "text/csv" });
}
