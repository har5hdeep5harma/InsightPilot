import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { ReportPreviewView } from "@/components/report/report-preview-view";
import { StatusBadge } from "@/components/ui/status-badge";

type ReportPreviewPageProps = {
  params: Promise<{
    datasetId: string;
  }>;
};

export default async function ReportPreviewPage({ params }: ReportPreviewPageProps) {
  const { datasetId } = await params;

  return (
    <AppShell>
      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <PageHeader
          label="Report Preview"
          title="Review the generated executive memo."
          description="This page calls the deterministic report generator and renders only sections returned by the backend."
          meta={
            <>
              <StatusBadge tone="success">Deterministic memo</StatusBadge>
              <StatusBadge>{`Dataset ${datasetId.slice(0, 8)}`}</StatusBadge>
            </>
          }
        />
        <div className="mt-8">
          <ReportPreviewView datasetId={datasetId} />
        </div>
      </main>
    </AppShell>
  );
}
