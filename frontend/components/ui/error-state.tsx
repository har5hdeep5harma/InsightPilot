import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

type ErrorStateProps = {
  title: string;
  description: string;
  detail?: string;
  action?: ReactNode;
  className?: string;
};

export function ErrorState({
  title,
  description,
  detail,
  action,
  className
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-red-200 bg-red-50/70 p-6 text-red-950",
        className
      )}
      role="alert"
    >
      <div className="flex gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" aria-hidden="true" />
        <div>
          <h3 className="text-body-sm font-semibold">{title}</h3>
          <p className="mt-1 text-body-sm text-red-800">{description}</p>
          {detail ? (
            <p className="mt-3 rounded-md border border-red-200 bg-white/70 px-3 py-2 font-mono text-caption text-red-700">
              {detail}
            </p>
          ) : null}
          {action ? <div className="mt-4">{action}</div> : null}
        </div>
      </div>
    </div>
  );
}
