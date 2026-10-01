import Link from "next/link";
import { BarChart3, FileText, Layers3, UploadCloud } from "lucide-react";
import { BrandMark } from "@/components/layout/brand-mark";

const navItems = [
  { label: "Profile", icon: Layers3 },
  { label: "Insights", icon: BarChart3 },
  { label: "Report", icon: FileText }
];

export function SidebarNavigation() {
  return (
    <aside className="hidden w-64 shrink-0 border-r bg-surface/90 px-4 py-5 lg:block">
      <Link href="/" className="flex items-center gap-3 rounded-md px-2 py-2">
        <BrandMark />
        <span>
          <span className="block text-body-sm font-semibold text-foreground">InsightPilot</span>
          <span className="block text-caption text-muted-foreground">Analysis Studio</span>
        </span>
      </Link>
      <nav className="mt-8 space-y-1" aria-label="Studio navigation">
        <Link
          href="/studio#ingest"
          className="flex h-9 items-center gap-3 rounded-md bg-secondary px-2.5 text-body-sm font-medium text-foreground transition-colors hover:bg-secondary/80"
        >
          <UploadCloud className="h-4 w-4" aria-hidden="true" />
          Ingest
        </Link>
        {navItems.map((item) => {
          const Icon = item.icon;

          return (
            <div
              key={item.label}
              className="flex h-9 items-center justify-between gap-3 rounded-md px-2.5 text-body-sm font-medium text-muted-foreground"
              aria-disabled="true"
            >
              <span className="flex items-center gap-3">
                <Icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </span>
              <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground/70">
                after upload
              </span>
            </div>
          );
        })}
      </nav>
      <div className="mt-10 rounded-md border bg-surface-raised p-3">
        <p className="text-caption font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Principle
        </p>
        <p className="mt-2 text-body-sm text-foreground">
          Reports lead the experience. Charts exist to support evidence.
        </p>
      </div>
    </aside>
  );
}
