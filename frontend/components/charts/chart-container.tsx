import type { ReactNode } from "react";
import { Panel } from "@/components/ui/panel";
import { SectionLabel } from "@/components/ui/section-label";
import { cn } from "@/lib/utils";

type ChartContainerProps = {
  title: string;
  description?: string;
  reasoning?: string;
  children: ReactNode;
  className?: string;
};

export function ChartContainer({
  title,
  description,
  reasoning,
  children,
  className
}: ChartContainerProps) {
  return (
    <Panel as="article" className={cn("overflow-hidden", className)}>
      <div className="border-b px-5 py-4">
        <SectionLabel
          title={title}
          description={description}
          action={
            reasoning ? (
              <span className="rounded-full border bg-secondary px-2.5 py-1 text-caption text-muted-foreground">
                Recommended
              </span>
            ) : null
          }
        />
        {reasoning ? (
          <p className="mt-3 text-caption text-muted-foreground">{reasoning}</p>
        ) : null}
      </div>
      <div className="min-h-72 p-5">{children}</div>
    </Panel>
  );
}
