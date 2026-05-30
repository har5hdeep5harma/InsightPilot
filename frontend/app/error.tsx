"use client";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";

type ErrorPageProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <ErrorState
        title="The studio surface could not load."
        description="The current view hit a rendering error. Retry keeps you in place and reloads this route."
        detail={error.digest ? `digest: ${error.digest}` : error.message}
        action={
          <Button type="button" size="sm" onClick={reset}>
            Retry
          </Button>
        }
      />
    </main>
  );
}
