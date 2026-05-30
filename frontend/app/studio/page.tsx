import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { UploadStudio } from "@/components/upload/upload-studio";
import { StatusBadge } from "@/components/ui/status-badge";

export default function StudioPage() {
  return (
    <AppShell>
      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <PageHeader
          label="Upload Studio"
          title="Bring in a spreadsheet. Get a reliable first read."
          description="Upload a CSV or XLSX file, or start with the sample dataset. InsightPilot will use the real backend parser and return an auditable preview before profiling."
          meta={
            <>
              <StatusBadge tone="success">Real upload API</StatusBadge>
              <StatusBadge tone="info">CSV/XLSX</StatusBadge>
              <StatusBadge>25 MB limit</StatusBadge>
            </>
          }
        />
        <div className="mt-8">
          <UploadStudio />
        </div>
      </main>
    </AppShell>
  );
}
