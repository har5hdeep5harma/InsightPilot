"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type LoadingStateProps = {
  title?: string;
  description?: string;
  className?: string;
};

export function LoadingState({
  title = "Preparing analysis",
  description = "Profiling the dataset and assembling the report surface.",
  className
}: LoadingStateProps) {
  return (
    <div className={cn("rounded-lg border bg-surface p-6 shadow-panel", className)}>
      <div className="flex items-center gap-3">
        <motion.span
          aria-hidden="true"
          className="h-2.5 w-2.5 rounded-full bg-accent"
          animate={{ opacity: [0.35, 1, 0.35] }}
          transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
        />
        <div>
          <p className="text-body-sm font-medium text-foreground">{title}</p>
          <p className="mt-1 text-caption text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="mt-5 space-y-2">
        <div className="h-2 w-5/6 animate-pulse rounded-full bg-secondary" />
        <div className="h-2 w-2/3 animate-pulse rounded-full bg-secondary" />
      </div>
    </div>
  );
}
