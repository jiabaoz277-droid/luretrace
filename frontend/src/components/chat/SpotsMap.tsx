"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { Spot } from "@/types/api";

const AMAP_JS_KEY = process.env.NEXT_PUBLIC_AMAP_JS_KEY || "";
const AMAP_SECURITY = process.env.NEXT_PUBLIC_AMAP_SECURITY_CODE || "";

const COLORS: Record<string, string> = {
  回水湾: "#2563eb",
  入水口: "#16a34a",
  钓场: "#ea580c",
  水域: "#0891b2",
  近岸: "#9333ea",
  收藏钓点: "#f59e0b",
};

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// 模块级缓存，避免重复加载高德 JS
let amapPromise: Promise<any> | null = null;

function loadAMap(): Promise<any> {
  if (amapPromise) return amapPromise;
  amapPromise = new Promise((resolve, reject) => {
    const w = window as any;
    if (w.AMap) {
      resolve(w.AMap);
      return;
    }
    // 安全密钥必须在 JS API 加载前设置
    w._AMapSecurityConfig = { securityJsCode: AMAP_SECURITY };
    const script = document.createElement("script");
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${AMAP_JS_KEY}`;
    script.onload = () => resolve(w.AMap);
    script.onerror = () => {
      amapPromise = null;
      reject(new Error("高德地图加载失败"));
    };
    document.head.appendChild(script);
  });
  return amapPromise;
}

async function saveFavorite(s: Spot) {
  try {
    const res = await apiFetch("/api/v1/spots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: s.name, location: s.name, lat: s.lat, lon: s.lon }),
    });
    if (res.ok) {
      alert(`已收藏「${s.name}」`);
    } else {
      alert("收藏失败，请稍后再试");
    }
  } catch {
    alert("收藏失败，请稍后再试");
  }
}

export function SpotsMap({ spots }: { spots: Spot[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || mapRef.current || spots.length === 0) return;
    let cancelled = false;

    loadAMap()
      .then((AMap) => {
        if (cancelled || !containerRef.current) return;

        const lngs = spots.map((s) => s.lon);
        const lats = spots.map((s) => s.lat);
        const center: [number, number] = [
          (Math.min(...lngs) + Math.max(...lngs)) / 2,
          (Math.min(...lats) + Math.max(...lats)) / 2,
        ];

        const map = new AMap.Map(container, {
          zoom: 12,
          center,
          viewMode: "2D",
        });
        mapRef.current = map;

        const markers = spots.map((s) => {
          const color = COLORS[s.spot_type] || "#64748b";
          const marker = new AMap.Marker({
            position: [s.lon, s.lat],
            content: `<div style="width:16px;height:16px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,.45)"></div>`,
            offset: new AMap.Pixel(-8, -8),
          });
          marker.setMap(map);

          const infoWindow = new AMap.InfoWindow({
            content: `<div style="font-size:12px;line-height:1.6;max-width:220px">
              <b>${escapeHtml(s.name)} · ${escapeHtml(s.spot_type)}</b><br/>
              距你约 ${s.distance_km} 公里<br/>
              <span style="color:#666">${escapeHtml(s.reason)}</span>
            </div>`,
            offset: new AMap.Pixel(0, -18),
          });
          marker.on("click", () => {
            infoWindow.open(map, marker.getPosition());
          });
          return marker;
        });

        if (markers.length > 0) {
          map.setFitView(markers, false, [60, 60, 60, 60]);
        }
      })
      .catch((e) => {
        setError(e?.message || "地图加载失败");
      });

    return () => {
      cancelled = true;
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
      }
    };
  }, [spots]);

  return (
    <div className="mt-2 overflow-hidden rounded-xl border border-line">
      <div ref={containerRef} className="h-52 w-full" />
      {error && (
        <div className="bg-surface px-3 py-2 text-xs text-accent">
          {error}（点位列表仍可参考）
        </div>
      )}
      <div className="flex flex-wrap gap-x-3 gap-y-1 bg-surface px-3 py-2 text-xs text-ink-soft">
        {spots.map((s, i) => (
          <span key={i} className="flex items-center gap-1">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: COLORS[s.spot_type] || "#64748b" }}
            />
            {s.name}·{s.spot_type}
            {s.spot_type !== "收藏钓点" && (
              <button
                onClick={() => saveFavorite(s)}
                className="ml-1 rounded border border-daiwa/30 px-1.5 py-0.5 text-[10px] text-daiwa hover:bg-daiwa/10"
              >
                收藏
              </button>
            )}
          </span>
        ))}
      </div>
    </div>
  );
}
