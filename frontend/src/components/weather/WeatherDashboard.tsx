"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import type { Dashboard } from "@/types/api";

const SpotsMap = dynamic(
  () => import("@/components/chat/SpotsMap").then((m) => m.SpotsMap),
  { ssr: false }
);

export function WeatherDashboard({ onClose }: { onClose: () => void }) {
  const [place, setPlace] = useState("");
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(p?: string) {
    const q = (p ?? place).trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/v1/dashboard?place=${encodeURIComponent(q)}`);
      const d = (await res.json()) as Dashboard;
      setData(d);
    } catch {
      setError("查询失败，请稍后再试");
    } finally {
      setLoading(false);
    }
  }

  const c = data?.current;

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-2xl bg-surface p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-bold text-ink">实时天气 · 附近钓点</h2>
          <button onClick={onClose} className="text-sm text-ink-soft">
            关闭
          </button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
          className="mb-3 flex gap-2"
        >
          <input
            value={place}
            onChange={(e) => setPlace(e.target.value)}
            placeholder="输入城市或水域，如 杭州 / 富春江"
            className="min-h-10 flex-1 rounded-full border border-line bg-paper px-4 py-2 text-sm outline-none focus:border-daiwa"
          />
          <button
            type="submit"
            disabled={loading || !place.trim()}
            className="rounded-full bg-daiwa px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {loading ? "查询中…" : "查看"}
          </button>
        </form>

        {error && <p className="text-sm text-accent">{error}</p>}

        {data && (
          <div className="max-h-[70vh] overflow-y-auto">
            {c && (
              <div className="mb-3 rounded-xl border border-line bg-paper p-4">
                <div className="text-sm text-ink-soft">
                  {data.location}
                  {data.mock ? "（模拟数据）" : ""}
                </div>
                <div className="mt-1 flex items-end gap-2">
                  <span className="text-3xl font-bold text-ink">{c.temp}℃</span>
                  <span className="text-sm text-ink-soft">{c.condition}</span>
                </div>
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-soft">
                  <span>
                    {c.wind_dir}
                    {c.wind_scale}级
                  </span>
                  <span>气压 {c.pressure} hPa</span>
                  <span>降水概率 {c.precip_prob}%</span>
                </div>
                <div className="mt-2 text-xs text-ink-soft">
                  日出 {data.sunrise} · 日落 {data.sunset}
                </div>
              </div>
            )}

            {data.spots.length > 0 ? (
              <div>
                <p className="mb-2 text-sm font-semibold text-ink">附近钓点</p>
                <SpotsMap spots={data.spots} />
              </div>
            ) : (
              <p className="text-sm text-ink-soft">附近水域数据暂时没查到。</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
