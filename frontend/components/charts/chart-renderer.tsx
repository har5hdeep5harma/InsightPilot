"use client";

import { Fragment, type ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { ChartSpec } from "@/types/api";
import { cn } from "@/lib/utils";

const CHART_BLUE = "#2563eb";
const CHART_EMERALD = "#059669";
const CHART_VIOLET = "#7c3aed";
const CHART_AMBER = "#d97706";
const CHART_SLATE = "#475569";
const STACK_COLORS = [CHART_BLUE, CHART_EMERALD, CHART_VIOLET, CHART_AMBER, CHART_SLATE];

type ChartRendererProps = {
  chart: ChartSpec;
};

export function ChartRenderer({ chart }: ChartRendererProps) {
  if (!chart.chart_data.length) {
    return (
      <div className="flex h-72 items-center justify-center rounded-lg border border-dashed bg-surface-raised text-body-sm text-muted-foreground">
        No chart data returned by the backend.
      </div>
    );
  }

  if (chart.chart_type === "line") {
    return <LineChartRenderer chart={chart} />;
  }

  if (chart.chart_type === "bar") {
    return <BarChartRenderer chart={chart} layout="vertical" />;
  }

  if (chart.chart_type === "horizontal_bar") {
    return <BarChartRenderer chart={chart} layout="horizontal" />;
  }

  if (chart.chart_type === "histogram") {
    return <BarChartRenderer chart={chart} layout="vertical" />;
  }

  if (chart.chart_type === "scatter") {
    return <ScatterChartRenderer chart={chart} />;
  }

  if (chart.chart_type === "correlation_heatmap") {
    return <CorrelationHeatmap chart={chart} />;
  }

  if (chart.chart_type === "stacked_bar") {
    return <StackedBarChartRenderer chart={chart} />;
  }

  if (chart.chart_type === "box_plot") {
    return <BoxPlotRenderer chart={chart} />;
  }

  return (
    <div className="flex h-72 items-center justify-center rounded-lg border border-dashed bg-surface-raised text-body-sm text-muted-foreground">
      Unsupported chart type: {chart.chart_type}
    </div>
  );
}

function LineChartRenderer({ chart }: ChartRendererProps) {
  const xKey = chart.x_column ?? "x";
  const yKey = chart.y_column ?? "y";

  return (
    <ChartFrame>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chart.chart_data} margin={{ top: 12, right: 24, left: 8, bottom: 24 }}>
          <CartesianGrid stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey={xKey} tick={axisTick} minTickGap={24} />
          <YAxis tick={axisTick} width={64} tickFormatter={formatAxisNumber} />
          <Tooltip content={<ChartTooltip />} />
          <Line
            type="monotone"
            dataKey={yKey}
            stroke={CHART_BLUE}
            strokeWidth={2}
            dot={{ r: 3, strokeWidth: 1 }}
            activeDot={{ r: 5 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

function BarChartRenderer({
  chart,
  layout
}: ChartRendererProps & { layout: "vertical" | "horizontal" }) {
  const xKey = chart.x_column ?? "x";
  const yKey = chart.y_column ?? "y";
  const isHorizontal = layout === "horizontal";

  return (
    <ChartFrame heightClass={isHorizontal ? "h-[360px]" : "h-80"}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chart.chart_data}
          layout={isHorizontal ? "vertical" : "horizontal"}
          margin={{ top: 12, right: 24, left: isHorizontal ? 72 : 8, bottom: 24 }}
        >
          <CartesianGrid stroke="#e2e8f0" horizontal={!isHorizontal} vertical={isHorizontal} />
          {isHorizontal ? (
            <>
              <XAxis type="number" tick={axisTick} tickFormatter={formatAxisNumber} />
              <YAxis type="category" dataKey={yKey} tick={axisTick} width={96} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey={xKey} fill={CHART_BLUE} radius={[0, 4, 4, 0]} isAnimationActive={false} />
            </>
          ) : (
            <>
              <XAxis dataKey={xKey} tick={axisTick} interval={0} angle={-18} textAnchor="end" height={64} />
              <YAxis tick={axisTick} width={64} tickFormatter={formatAxisNumber} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey={yKey} fill={CHART_BLUE} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </>
          )}
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

function ScatterChartRenderer({ chart }: ChartRendererProps) {
  const xKey = chart.x_column ?? "x";
  const yKey = chart.y_column ?? "y";

  return (
    <ChartFrame>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 12, right: 24, left: 8, bottom: 24 }}>
          <CartesianGrid stroke="#e2e8f0" />
          <XAxis dataKey={xKey} type="number" name={xKey} tick={axisTick} tickFormatter={formatAxisNumber} />
          <YAxis dataKey={yKey} type="number" name={yKey} tick={axisTick} tickFormatter={formatAxisNumber} width={64} />
          <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: "3 3" }} />
          <Scatter data={chart.chart_data} fill={CHART_BLUE} isAnimationActive={false} />
        </ScatterChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

function StackedBarChartRenderer({ chart }: ChartRendererProps) {
  const xKey = chart.x_column ?? "x";
  const stackKeys = Object.keys(chart.chart_data[0] ?? {}).filter((key) => key !== xKey);

  return (
    <ChartFrame>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chart.chart_data} margin={{ top: 12, right: 24, left: 8, bottom: 28 }}>
          <CartesianGrid stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey={xKey} tick={axisTick} interval={0} angle={-18} textAnchor="end" height={64} />
          <YAxis tick={axisTick} width={64} tickFormatter={formatAxisNumber} />
          <Tooltip content={<ChartTooltip />} />
          {stackKeys.map((key, index) => (
            <Bar
              key={key}
              dataKey={key}
              stackId="stack"
              fill={STACK_COLORS[index % STACK_COLORS.length]}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

function CorrelationHeatmap({ chart }: ChartRendererProps) {
  const metrics = Array.from(
    new Set(
      chart.chart_data.flatMap((row) => [
        String(row.metric_x ?? ""),
        String(row.metric_y ?? "")
      ])
    )
  ).filter(Boolean);

  return (
    <div className="overflow-auto rounded-lg border bg-surface p-4">
      <div
        className="grid min-w-[520px] gap-1"
        style={{ gridTemplateColumns: `120px repeat(${metrics.length}, minmax(64px, 1fr))` }}
      >
        <div />
        {metrics.map((metric) => (
          <div key={metric} className="truncate px-2 py-1 text-center text-caption text-muted-foreground">
            {metric}
          </div>
        ))}
        {metrics.map((yMetric) => (
          <Fragment key={yMetric}>
            <div key={`${yMetric}-label`} className="truncate px-2 py-3 text-caption font-medium text-muted-foreground">
              {yMetric}
            </div>
            {metrics.map((xMetric) => {
              const value = Number(
                chart.chart_data.find(
                  (row) => row.metric_x === xMetric && row.metric_y === yMetric
                )?.correlation ?? 0
              );
              return (
                <div
                  key={`${xMetric}-${yMetric}`}
                  className="flex h-12 items-center justify-center rounded-sm text-caption font-medium"
                  style={{
                    backgroundColor: correlationColor(value),
                    color: Math.abs(value) > 0.65 ? "#ffffff" : "#0f172a"
                  }}
                  title={`${xMetric} vs ${yMetric}: ${value.toFixed(2)}`}
                >
                  {value.toFixed(2)}
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );
}

function BoxPlotRenderer({ chart }: ChartRendererProps) {
  const categoryKey = chart.x_column ?? Object.keys(chart.chart_data[0] ?? {})[0];

  return (
    <div className="space-y-3 rounded-lg border bg-surface p-4">
      {chart.chart_data.map((row) => {
        const min = asNumber(row.min);
        const q1 = asNumber(row.q1);
        const median = asNumber(row.median);
        const q3 = asNumber(row.q3);
        const max = asNumber(row.max);
        const range = max - min || 1;
        const left = ((q1 - min) / range) * 100;
        const width = ((q3 - q1) / range) * 100;
        const medianLeft = ((median - min) / range) * 100;

        return (
          <div key={String(row[categoryKey])} className="grid gap-2 sm:grid-cols-[140px_minmax(0,1fr)] sm:items-center">
            <p className="truncate text-caption font-medium text-muted-foreground">{String(row[categoryKey])}</p>
            <div className="relative h-10">
              <div className="absolute left-0 right-0 top-1/2 h-px bg-border" />
              <div
                className="absolute top-2 h-6 rounded-sm border border-blue-300 bg-blue-50"
                style={{ left: `${left}%`, width: `${Math.max(width, 1)}%` }}
              />
              <div
                className="absolute top-1 h-8 w-px bg-blue-700"
                style={{ left: `${medianLeft}%` }}
              />
              <div className="absolute left-0 top-7 text-[10px] text-muted-foreground">{formatAxisNumber(min)}</div>
              <div className="absolute right-0 top-7 text-[10px] text-muted-foreground">{formatAxisNumber(max)}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ChartFrame({
  children,
  heightClass = "h-80"
}: {
  children: ReactNode;
  heightClass?: string;
}) {
  return (
    <div className={cn("rounded-lg border bg-surface p-3", heightClass)}>
      {children}
    </div>
  );
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="rounded-md border bg-surface px-3 py-2 text-caption shadow-panel">
      {label !== undefined ? <p className="mb-1 font-medium text-foreground">{String(label)}</p> : null}
      <div className="space-y-1">
        {payload.map((item: any) => (
          <p key={`${item.name}-${item.value}`} className="text-muted-foreground">
            <span className="font-medium text-foreground">{item.name}:</span>{" "}
            {formatTooltipValue(item.value)}
          </p>
        ))}
      </div>
    </div>
  );
}

const axisTick = {
  fill: "#64748b",
  fontSize: 11
};

function formatAxisNumber(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return String(value);
  }
  if (Math.abs(number) >= 1_000_000) {
    return `${(number / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(number) >= 1_000) {
    return `${(number / 1_000).toFixed(1)}k`;
  }
  return Number.isInteger(number) ? String(number) : number.toFixed(1);
}

function formatTooltipValue(value: unknown) {
  if (typeof value === "number") {
    return formatAxisNumber(value);
  }
  return String(value);
}

function correlationColor(value: number) {
  const clamped = Math.max(-1, Math.min(1, value));
  if (clamped >= 0) {
    const alpha = 0.12 + Math.abs(clamped) * 0.72;
    return `rgba(37, 99, 235, ${alpha})`;
  }
  const alpha = 0.12 + Math.abs(clamped) * 0.72;
  return `rgba(217, 119, 6, ${alpha})`;
}

function asNumber(value: unknown) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}
