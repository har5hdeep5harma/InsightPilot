import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { DatasetProfileView } from "@/components/profile/dataset-profile-view";
import { StatusBadge } from "@/components/ui/status-badge";

type DatasetProfilePageProps = {
  params: Promise<{
    datasetId: string;
  }>;
};

export default async function DatasetProfilePage({ params }: DatasetProfilePageProps) {
  const { datasetId } = await params;

  return (
    <AppShell>
      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <PageHeader
          label="Dataset Profile"
          title="Inspect the dataset before generating insights."
          description="The profile view calls the real backend profiling service for the uploaded dataset."
          meta={
            <>
              <StatusBadge tone="success">Computed profile</StatusBadge>
              <StatusBadge>{`Dataset ${datasetId.slice(0, 8)}`}</StatusBadge>
            </>
          }
        />
        <div className="mt-8">
          <DatasetProfileView datasetId={datasetId} />
        </div>
      </main>
    </AppShell>
  );
}
