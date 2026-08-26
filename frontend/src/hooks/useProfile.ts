"use client";

import { useCallback, useEffect, useState } from "react";
import type { ProfileData } from "@/types/api";
import { apiFetch } from "@/lib/api";

const EMPTY: ProfileData = {
  rods: [],
  reels: [],
  lines: [],
  lures: [],
  avoid_methods: [],
  night_fishing: false,
  wading: false,
  constraints: [],
};

/** 装备偏好读取与保存。 */
export function useProfile() {
  const [profile, setProfile] = useState<ProfileData>(EMPTY);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    apiFetch("/api/v1/profile")
      .then((r) => (r.ok ? r.json() : EMPTY))
      .then((p) => setProfile({ ...EMPTY, ...p }))
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  const save = useCallback(async (data: ProfileData) => {
    await apiFetch("/api/v1/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    setProfile(data);
  }, []);

  return { profile, loaded, save };
}
