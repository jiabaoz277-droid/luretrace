"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { Dashboard } from "@/types/api";

export type DashboardCoordinates = { lat: number; lon: number };

export function useDashboardData({
  place,
  coordinates,
  species,
  travelMinutes,
}: {
  place: string;
  coordinates?: DashboardCoordinates | null;
  species?: string;
  travelMinutes?: number;
}) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!place.trim() && !coordinates) return;
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (place.trim()) params.set("place", place.trim());
        if (coordinates) {
          params.set("lat", String(coordinates.lat));
          params.set("lon", String(coordinates.lon));
        }
        if (species) params.set("target_species", species);
        if (travelMinutes) params.set("max_travel_minutes", String(travelMinutes));

        const response = await apiFetch(`/api/v1/dashboard?${params}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        setData((await response.json()) as Dashboard);
      } catch (reason) {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError("实时天气或钓点暂时加载失败，请稍后重试");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void load();
    return () => controller.abort();
  }, [coordinates, place, species, travelMinutes]);

  return { data, loading, error };
}
