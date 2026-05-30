"use client";

import { useEffect, useState } from "react";
import { Activity, Database, Search } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { API_BASE_URL } from "@/lib/api-client";

type BackendStatus = "checking" | "online" | "offline";

export function TopCommandBar() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");

  useEffect(() => {
    let cancelled = false;

    async function checkBackend() {
      try {
        const response = await fetch(`${API_BASE_URL}/health`, {
          headers: { Accept: "application/json" },
          cache: "no-store"
        });
        if (!cancelled) {
          setBackendStatus(response.ok ? "online" : "offline");
        }
      } catch {
        if (!cancelled) {
          setBackendStatus("offline");
        }
      }
    }

    void checkBackend();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="flex h-14 items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div className="hidden h-8 w-80 items-center gap-2 rounded-md border bg-surface px-3 text-muted-foreground shadow-hairline md:flex">
            <Search className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="text-caption">Upload, parse, profile, and report from one studio.</span>
          </div>
          <StatusBadge tone={backendStatus === "online" ? "success" : backendStatus === "offline" ? "danger" : "neutral"}>
            {backendStatus === "online" ? "Backend online" : backendStatus === "offline" ? "Backend offline" : "Checking backend"}
          </StatusBadge>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="hidden items-center gap-1.5 text-caption text-muted-foreground sm:flex">
            <Database className="h-3.5 w-3.5" aria-hidden="true" />
            SQLite local
          </span>
          <span className="hidden items-center gap-1.5 text-caption text-muted-foreground sm:flex">
            <Activity className="h-3.5 w-3.5" aria-hidden="true" />
            Deterministic
          </span>
        </div>
      </div>
    </header>
  );
}
