import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type ReportPageContainerProps = {
  children: ReactNode;
  className?: string;
};

export function ReportPageContainer({ children, className }: ReportPageContainerProps) {
  return (
    <article
      className={cn(
        "mx-auto max-w-4xl rounded-lg border bg-surface px-6 py-8 shadow-panel sm:px-10 sm:py-12",
        className
      )}
    >
      {children}
    </article>
  );
}
