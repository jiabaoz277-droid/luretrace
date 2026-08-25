"use client";

import { useState } from "react";
import { useProfile } from "@/hooks/useProfile";
import type { ProfileData } from "@/types/api";

export function ProfilePanel({ onClose }: { onClose: () => void }) {
  const { profile, loaded, save } = useProfile();

  if (!loaded) {
    return (
      <div className="fixed inset-0 z-10 flex items-end justify-center bg-black/40" onClick={onClose}>
        <div
          className="w-full max-w-md rounded-t-2xl bg-surface p-5"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="text-sm text-ink-soft">加载中…</p>
        </div>
      </div>
    );
  }

  return <ProfileForm initial={profile} onSave={save} onClose={onClose} />;
}

function ProfileForm({
  initial,
  onSave,
  onClose,
}: {
  initial: ProfileData;
  onSave: (p: ProfileData) => Promise<void>;
  onClose: () => void;
}) {
  const [lures, setLures] = useState((initial.lures || []).join("、"));
  const [radius, setRadius] = useState(initial.max_travel_radius || "");
  const [noNight, setNoNight] = useState((initial.constraints || []).includes("不夜钓"));
  const [noWading, setNoWading] = useState((initial.constraints || []).includes("不涉水"));
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    const constraints: string[] = [];
    if (noNight) constraints.push("不夜钓");
    if (noWading) constraints.push("不涉水");
    await onSave({
      ...initial,
      lures: lures.split(/[,，、]/).map((s) => s.trim()).filter(Boolean),
      max_travel_radius: radius || null,
      constraints,
    });
    setSaved(true);
    setTimeout(onClose, 700);
  }

  return (
    <div className="fixed inset-0 z-10 flex items-end justify-center bg-black/40" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-t-2xl bg-surface p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center gap-2">
          <span className="h-4 w-1 rounded bg-daiwa" />
          <h2 className="text-base font-bold text-ink">我的装备与偏好</h2>
        </div>

        <label className="mb-3 block text-sm">
          <span className="text-ink-soft">常用拟饵（逗号分隔）</span>
          <input
            value={lures}
            onChange={(e) => setLures(e.target.value)}
            placeholder="如：7g亮片、米诺"
            className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-daiwa"
          />
        </label>

        <label className="mb-3 block text-sm">
          <span className="text-ink-soft">最大车程</span>
          <input
            value={radius}
            onChange={(e) => setRadius(e.target.value)}
            placeholder="如：40分钟"
            className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-daiwa"
          />
        </label>

        <div className="mb-4 flex gap-6 text-sm text-ink">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={noNight} onChange={(e) => setNoNight(e.target.checked)} />
            不夜钓
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={noWading} onChange={(e) => setNoWading(e.target.checked)} />
            不涉水
          </label>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleSave}
            className="flex-1 rounded-full bg-daiwa py-2.5 text-sm font-semibold text-white"
          >
            {saved ? "已保存 ✓" : "保存"}
          </button>
          <button
            onClick={onClose}
            className="rounded-full border border-line px-5 py-2.5 text-sm text-ink-soft"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
