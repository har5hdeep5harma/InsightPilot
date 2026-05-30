import type { ChartSpec } from "@/types/api";

const STORAGE_PREFIX = "insightpilot.reportCharts";

export function reportChartSelectionKey(datasetId: string) {
  return `${STORAGE_PREFIX}.${datasetId}`;
}

export function defaultIncludedChartIds(charts: ChartSpec[]) {
  return charts.map((chart) => chart.id);
}

export function loadIncludedChartIds(datasetId: string, charts: ChartSpec[]) {
  if (typeof window === "undefined") {
    return defaultIncludedChartIds(charts);
  }

  const validIds = new Set(charts.map((chart) => chart.id));
  const stored = window.localStorage.getItem(reportChartSelectionKey(datasetId));
  if (!stored) {
    return defaultIncludedChartIds(charts);
  }

  try {
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) {
      return defaultIncludedChartIds(charts);
    }

    return parsed
      .map(String)
      .filter((chartId) => validIds.has(chartId));
  } catch {
    return defaultIncludedChartIds(charts);
  }
}

export function saveIncludedChartIds(datasetId: string, chartIds: string[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    reportChartSelectionKey(datasetId),
    JSON.stringify(chartIds)
  );
}
