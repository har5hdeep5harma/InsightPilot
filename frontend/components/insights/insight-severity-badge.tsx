import { cn } from "@/lib/utils";

type InsightSeverity = "low" | "medium" | "high";

type InsightSeverityBadgeProps = {
  severity: InsightSeverity;
  className?: string;
};

const severityStyles: Record<InsightSeverity, string> = {
  low: "border-emerald-200 bg-emerald-50 text-emerald-700",
  medium: "border-amber-200 bg-amber-50 text-amber-700",
  high: "border-red-200 bg-red-50 text-red-700"
};

export function InsightSeverityBadge({
  severity,
  className
}: InsightSeverityBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center rounded-full border px-2.5 text-caption font-medium capitalize",
        severityStyles[severity],
        className
      )}
    >
      {severity}
    </span>
  );
}
