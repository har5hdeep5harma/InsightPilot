import { CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

type EvidenceBadgeProps = {
  label?: string;
  className?: string;
};

export function EvidenceBadge({
  label = "Evidence attached",
  className
}: EvidenceBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-2.5 text-caption font-medium text-blue-700",
        className
      )}
    >
      <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
      {label}
    </span>
  );
}
