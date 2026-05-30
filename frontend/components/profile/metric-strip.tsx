import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type MetricStripItem = {
  label: string;
  value: string;
  detail?: string;
  icon?: ReactNode;
};

type MetricStripProps = {
  items: MetricStripItem[];
  className?: string;
};

export function MetricStrip({ items, className }: MetricStripProps) {
  return (
    <dl className={cn("grid gap-3 sm:grid-cols-2 xl:grid-cols-4", className)}>
      {items.map((item) => (
        <div
          key={item.label}
          className="rounded-lg border bg-surface px-4 py-3 shadow-panel"
        >
          <dt className="flex items-center gap-2 text-caption font-medium uppercase tracking-[0.12em] text-muted-foreground">
            {item.icon}
            {item.label}
          </dt>
          <dd className="mt-3 text-heading-md font-semibold text-foreground">{item.value}</dd>
          {item.detail ? (
            <p className="mt-1 text-caption text-muted-foreground">{item.detail}</p>
          ) : null}
        </div>
      ))}
    </dl>
  );
}
