import { useEffect, useState } from "react";

import { apiClient } from "../api/client";

export function useBackendHealth() {
  const [health, setHealth] = useState("checking");

  useEffect(() => {
    let mounted = true;

    async function loadHealth() {
      try {
        const response = await apiClient.get("/health");
        if (mounted) {
          setHealth(response.data.status || "ok");
        }
      } catch {
        if (mounted) {
          setHealth("unreachable");
        }
      }
    }

    loadHealth();

    return () => {
      mounted = false;
    };
  }, []);

  return health;
}
