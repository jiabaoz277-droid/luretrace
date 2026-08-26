"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { Dashboard } from "@/types/api";
import { FishScoreChart } from "./FishScoreChart";

const SpotsMap = dynamic(
  () => import("@/components/chat/SpotsMap").then((m) => m.SpotsMap),
  { ssr: false }
);

export function LivePanel({
  location,
  onSend,
  onLocated,
}: {
  location?: string | null;
  onSend: (text: string) => void;
  onLocated?: (name: string) => void;
}) {
  const [place, setPlace] = useState(location || "");
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(false);

  async function load(p: string) {
    const q = p.trim();
    if (!q) return;
    setPlace(q);
    setLoading(true);
    try {
      const res = await apiFetch(`/api/v1/dashboard?place=${encodeURIComponent(q)}`);
      setData((await res.json()) as Dashboard);
      onLocated?.(q); // 同步给上层，保持对话框与底部位置一致
    } catch {
      // 保持上一次数据
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (place) load(place);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 用户授权定位或手动确认地点后，天气/钓点及时切换
  useEffect(() => {
    if (location && location !== place) {
      setPlace(location);
      load(location);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location]);

  const c = data?.current;

  function askHour(hour: number) {
    const end = (hour + 2) % 24;
    const loc = place.trim() || "这里";
    onSend(`今天${hour}点到${end}点去${loc}钓行不行`);
  }

  return (
    <section className="lure-live-panel">
      <div className="lure-live-head">
        <h2>实时天气 · 附近钓点</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            load(place);
          }}
        >
          <input
            value={place}
            onChange={(e) => setPlace(e.target.value)}
            placeholder="杭州 / 富春江"
            aria-label="地点"
          />
          <button type="submit">{loading ? "加载中…" : "查看"}</button>
        </form>
      </div>

      <div className="lure-live-grid">
        <div className="lure-weather-card">
          {c ? (
            <>
              <div className="lure-weather-main">
                <span className="lure-temp">{c.temp}℃</span>
                <div>
                  <strong>{c.condition}</strong>
                  <small>
                    {data?.location}
                    {data?.mock ? "（模拟数据）" : ""}
                  </small>
                </div>
              </div>
              <div className="lure-weather-meta">
                <span>
                  {c.wind_dir}
                  {c.wind_scale}级
                </span>
                <span>气压 {c.pressure} hPa</span>
                <span>降水 {c.precip_prob}%</span>
                <span>
                  日出 {data?.sunrise} · 日落 {data?.sunset}
                </span>
              </div>
            </>
          ) : (
            <p className="lure-weather-empty">
              {!place
                ? "请先定位或输入城市"
                : loading
                  ? "正在加载实时天气…"
                  : "暂无天气数据"}
            </p>
          )}
        </div>

        <div className="lure-spots-box">
          {data && data.spots.length > 0 ? (
            <SpotsMap spots={data.spots} />
          ) : (
            <p className="lure-weather-empty">
              {!place
                ? "定位或输入城市后，显示附近水域"
                : loading
                  ? "正在加载附近钓点…"
                  : "附近水域数据暂时没查到"}
            </p>
          )}
        </div>
      </div>

      {data && data.fish_scores.length > 0 && (
        <FishScoreChart scores={data.fish_scores} onAsk={askHour} />
      )}
    </section>
  );
}
