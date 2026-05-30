import { InsightBoardView } from "@/components/insights/insight-board-view";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { StatusBadge } from "@/components/ui/status-badge";

type InsightBoardPageProps = {
  params: Promise<{
    datasetId: string;
  }>;
};

export default async function InsightBoardPage({ params }: InsightBoardPageProps) {
  const { datasetId } = await params;

  return (
    <AppShell>
      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <PageHeader
          label="Insight Board"
          title="Generate deterministic, evidence-backed insights."
          description="This view calls the real insight generation endpoint and only renders findings returned by the backend."
          meta={
            <>
              <StatusBadge tone="success">Evidence required</StatusBadge>
              <StatusBadge>{`Dataset ${datasetId.slice(0, 8)}`}</StatusBadge>
            </>
          }
        />
        <div className="mt-8">
          <InsightBoardView datasetId={datasetId} />
        </div>
      </main>
    </AppShell>
  );
}
