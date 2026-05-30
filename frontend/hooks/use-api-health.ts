"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api-client";
import type { HealthResponse } from "@/types/api";

export function useApiHealth() {
  const [status, setStatus] = useState<HealthResponse["status"] | "unknown">(
    "unknown"
  );

  useEffect(() => {
    let isMounted = true;

    apiGet<HealthResponse>("/health")
      .then((response) => {
        if (isMounted) {
          setStatus(response.status);
        }
      })
      .catch(() => {
        if (isMounted) {
          setStatus("unknown");
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return status;
}
