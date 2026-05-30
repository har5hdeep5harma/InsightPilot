import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

type PanelProps = HTMLAttributes<HTMLElement> & {
  as?: "article" | "section" | "div";
  tone?: "default" | "subtle" | "inverse";
  children: ReactNode;
};

export function Panel({
  as: Comp = "section",
  tone = "default",
  className,
  children,
  ...props
}: PanelProps) {
  return (
    <Comp
      className={cn(
        "rounded-lg border shadow-panel transition-shadow duration-200 ease-productive",
        tone === "default" && "border-border bg-surface",
        tone === "subtle" && "border-border/80 bg-surface-raised",
        tone === "inverse" && "border-graphite-800 bg-surface-inverse text-primary-foreground",
        className
      )}
      {...props}
    >
      {children}
    </Comp>
  );
}
