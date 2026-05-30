import { ChartGalleryView } from "@/components/charts/chart-gallery-view";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { StatusBadge } from "@/components/ui/status-badge";

type ChartGalleryPageProps = {
  params: Promise<{
    datasetId: string;
  }>;
};

export default async function ChartGalleryPage({ params }: ChartGalleryPageProps) {
  const { datasetId } = await params;

  return (
    <AppShell>
      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <PageHeader
          label="Chart Gallery"
          title="Review the charts InsightPilot recommends."
          description="This view calls the real chart recommendation endpoint and shows only backend-generated chart specs."
          meta={
            <>
              <StatusBadge tone="success">Computed charts</StatusBadge>
              <StatusBadge>{`Dataset ${datasetId.slice(0, 8)}`}</StatusBadge>
            </>
          }
        />
        <div className="mt-8">
          <ChartGalleryView datasetId={datasetId} />
        </div>
      </main>
    </AppShell>
  );
}
