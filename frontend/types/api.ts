export type HealthResponse = {
  status: "ok";
};

export type ApiError = {
  code: string;
  message: string;
  technical_detail?: string;
  suggested_fix?: string;
  details?: Record<string, unknown>;
};

export type ApiErrorEnvelope = {
  error: ApiError;
};

export type DatasetColumn = {
  name: string;
  original_name: string;
};

export type AnalysisWarning = {
  code: string;
  message: string;
  column?: string | null;
  details?: Record<string, unknown>;
};

export type DatasetUploadResponse = {
  dataset_id: string;
  filename: string;
  row_count: number;
  column_count: number;
  columns: DatasetColumn[];
  preview_rows: Record<string, unknown>[];
  warnings: AnalysisWarning[];
};

export type DatasetPreviewResponse = {
  dataset_id: string;
  columns: DatasetColumn[];
  preview_rows: Record<string, unknown>[];
  limit: number;
  offset: number;
  row_count: number;
};

export type DatasetDetailResponse = {
  dataset_id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  row_count: number;
  column_count: number;
  uploaded_at: string;
  status: string;
  error_message?: string | null;
  columns: DatasetColumn[];
  warnings: AnalysisWarning[];
};

export type ColumnProfile = {
  name: string;
  original_name: string;
  inferred_type: string;
  role: string;
  missing_count: number;
  missing_percentage: number;
  unique_count: number;
  unique_percentage: number;
  sample_values: unknown[];
  min?: unknown;
  max?: unknown;
  mean?: number | null;
  median?: number | null;
  std?: number | null;
  top_values: Array<{
    value: unknown;
    count: number;
    percentage: number;
  }>;
  warnings: AnalysisWarning[];
};

export type DatasetProfile = {
  dataset_id: string;
  row_count: number;
  column_count: number;
  duplicate_row_count: number;
  memory_usage: number;
  columns: ColumnProfile[];
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns: string[];
  id_like_columns: string[];
  text_columns: string[];
  quality_score: number;
  warnings: AnalysisWarning[];
};

export type ChartSpec = {
  id: string;
  dataset_id: string;
  title: string;
  chart_type: string;
  x_column?: string | null;
  y_column?: string | null;
  group_by?: string | null;
  description: string;
  reasoning: string;
  priority: number;
  chart_data: Record<string, unknown>[];
};

export type Evidence = {
  type: string;
  column?: string | null;
  columns: string[];
  metric: string;
  value: unknown;
  comparison_value?: unknown;
  values: Record<string, unknown>;
  comparison_values: Record<string, unknown>;
  rows_affected?: number | null;
  calculation: string;
  explanation: string;
};

export type Insight = {
  id: string;
  dataset_id: string;
  title: string;
  summary: string;
  insight_type: string;
  severity: "low" | "medium" | "high";
  confidence: number;
  evidence: Evidence;
  recommendation?: string | null;
  related_columns: string[];
  related_chart_id?: string | null;
};

export type EvidenceAppendixItem = {
  insight_id: string;
  insight_title: string;
  insight_type: string;
  evidence: Evidence;
};

export type ReportResponse = {
  report_id: string;
  title: string;
  dataset_overview: string;
  executive_summary: string;
  key_findings: string[];
  risks: string[];
  opportunities: string[];
  recommendations: string[];
  data_quality_notes: string[];
  evidence_appendix: EvidenceAppendixItem[];
  chart_ids: string[];
};
