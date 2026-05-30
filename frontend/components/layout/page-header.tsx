import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type PageHeaderProps = {
  label?: string;
  title: string;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
  className?: string;
};

export function PageHeader({
  label,
  title,
  description,
  meta,
  actions,
  className
}: PageHeaderProps) {
  return (
    <header className={cn("flex flex-col gap-6 md:flex-row md:items-end md:justify-between", className)}>
      <div className="max-w-3xl">
        {label ? (
          <p className="text-caption font-medium uppercase tracking-[0.16em] text-muted-foreground">
            {label}
          </p>
        ) : null}
        <h1 className="mt-3 text-heading-lg font-semibold text-foreground sm:text-display-md">
          {title}
        </h1>
        {description ? (
          <p className="mt-4 max-w-2xl text-body text-muted-foreground">{description}</p>
        ) : null}
        {meta ? <div className="mt-5 flex flex-wrap items-center gap-2">{meta}</div> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  );
}
