import type { ApiErrorEnvelope } from "@/types/api";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiClientError extends Error {
  code: string;
  technicalDetail?: string;
  suggestedFix?: string;
  details?: Record<string, unknown>;
  status?: number;

  constructor({
    message,
    code,
    technicalDetail,
    suggestedFix,
    details,
    status
  }: {
    message: string;
    code: string;
    technicalDetail?: string;
    suggestedFix?: string;
    details?: Record<string, unknown>;
    status?: number;
  }) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.technicalDetail = technicalDetail;
    this.suggestedFix = suggestedFix;
    this.details = details;
    this.status = status;
  }
}

export async function apiGet<TResponse>(path: string): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    throw await toApiClientError(response);
  }

  return response.json() as Promise<TResponse>;
}

export async function apiPost<TResponse>(path: string, body?: unknown): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      ...(body === undefined ? {} : { "Content-Type": "application/json" })
    },
    body: body === undefined ? undefined : JSON.stringify(body)
  });

  if (!response.ok) {
    throw await toApiClientError(response);
  }

  return response.json() as Promise<TResponse>;
}

export async function toApiClientError(response: Response): Promise<ApiClientError> {
  const fallback = new ApiClientError({
    code: "API_REQUEST_FAILED",
    message: `API request failed with status ${response.status}.`,
    status: response.status
  });

  try {
    const body = (await response.json()) as Partial<ApiErrorEnvelope>;
    if (!body.error) {
      return fallback;
    }

    return new ApiClientError({
      code: body.error.code,
      message: body.error.message,
      technicalDetail: body.error.technical_detail,
      suggestedFix: body.error.suggested_fix,
      details: body.error.details,
      status: response.status
    });
  } catch {
    return fallback;
  }
}

export function normalizeUnknownError(error: unknown): ApiClientError {
  if (error instanceof ApiClientError) {
    return error;
  }

  if (error instanceof Error) {
    return new ApiClientError({
      code: "CLIENT_ERROR",
      message: error.message
    });
  }

  return new ApiClientError({
    code: "UNKNOWN_ERROR",
    message: "Something went wrong while contacting InsightPilot."
  });
}
