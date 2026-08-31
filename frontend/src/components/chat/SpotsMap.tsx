"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { Spot } from "@/types/api";
import type { Map as LeafletMap } from "leaflet";

const COLORS: Record<string, string> = {
  回水湾: "#4c8df0",
  入水口: "#3ecf7a",
  钓场: "#f08a3c",
  水域: "#33c4d6",
  近岸: "#b983f0",
  收藏钓点: "#f4b34a",
};

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const PI = Math.PI;
const AXIS = 6378245;
const ECCENTRICITY = 0.006693421622965943;

function outsideChina(lat: number, lon: number) {
  return lon < 72.004 || lon > 137.8347 || lat < 0.8293 || lat > 55.8271;
}

function transformLat(x: number, y: number) {
  let value = -100 + 2 * x + 3 * y + .2 * y * y + .1 * x * y + .2 * Math.sqrt(Math.abs(x));
  value += (20 * Math.sin(6 * x * PI) + 20 * Math.sin(2 * x * PI)) * 2 / 3;
  value += (20 * Math.sin(y * PI) + 40 * Math.sin(y / 3 * PI)) * 2 / 3;
  value += (160 * Math.sin(y / 12 * PI) + 320 * Math.sin(y * PI / 30)) * 2 / 3;
  return value;
}

function transformLon(x: number, y: number) {
  let value = 300 + x + 2 * y + .1 * x * x + .1 * x * y + .1 * Math.sqrt(Math.abs(x));
  value += (20 * Math.sin(6 * x * PI) + 20 * Math.sin(2 * x * PI)) * 2 / 3;
  value += (20 * Math.sin(x * PI) + 40 * Math.sin(x / 3 * PI)) * 2 / 3;
  value += (150 * Math.sin(x / 12 * PI) + 300 * Math.sin(x / 30 * PI)) * 2 / 3;
  return value;
}

/** 后端为高德展示返回 GCJ-02；OSM 使用 WGS-84，因此在显示层做逆转换。 */
export function gcj02ToWgs84(lat: number, lon: number): [number, number] {
  if (outsideChina(lat, lon)) return [lat, lon];
  let dLat = transformLat(lon - 105, lat - 35);
  let dLon = transformLon(lon - 105, lat - 35);
  const radLat = lat / 180 * PI;
  let magic = Math.sin(radLat);
  magic = 1 - ECCENTRICITY * magic * magic;
  const sqrtMagic = Math.sqrt(magic);
  dLat = dLat * 180 / ((AXIS * (1 - ECCENTRICITY)) / (magic * sqrtMagic) * PI);
  dLon = dLon * 180 / (AXIS / sqrtMagic * Math.cos(radLat) * PI);
  return [lat * 2 - (lat + dLat), lon * 2 - (lon + dLon)];
}

function popupContent(spot: Spot) {
  return `<div style="font-size:12px;line-height:1.6;max-width:220px">
    <b>${escapeHtml(spot.name)} · ${escapeHtml(spot.spot_type)}</b><br/>
    距你约 ${spot.distance_km} 公里<br/>
    <span style="color:#666">${escapeHtml(spot.reason)}</span>
  </div>`;
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
  const cleanupRef = useRef<(() => void) | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || cleanupRef.current || spots.length === 0) return;
    let cancelled = false;

    async function mountOsm() {
      try {
        const L = await import("leaflet");
        if (cancelled || !containerRef.current) return;
        const positions = spots.map((spot) => gcj02ToWgs84(spot.lat, spot.lon));
        const map: LeafletMap = L.map(containerRef.current, {
          zoomControl: true,
          attributionControl: true,
        });
        cleanupRef.current = () => map.remove();
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map);
        spots.forEach((spot, index) => {
          L.circleMarker(positions[index], {
            radius: 8,
            color: "#fff",
            weight: 2,
            fillColor: COLORS[spot.spot_type] || "#64748b",
            fillOpacity: 1,
          }).addTo(map).bindPopup(popupContent(spot));
        });
        map.fitBounds(L.latLngBounds(positions), { padding: [36, 36], maxZoom: 14 });
        setError(null);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "地图加载失败");
      }
    }

    void mountOsm();

    return () => {
      cancelled = true;
      cleanupRef.current?.();
      cleanupRef.current = null;
    };
  }, [spots]);

  return (
    <div className="mt-2 overflow-hidden rounded-xl border border-line">
      <div ref={containerRef} className="h-52 w-full" />
      <div className="bg-white/5 px-3 pt-2 text-[10px] text-ink-soft">地图：OpenStreetMap</div>
      {error && (
        <div className="bg-white/5 px-3 py-2 text-xs text-accent">
          {error}（点位列表仍可参考）
        </div>
      )}
      <div className="flex flex-wrap gap-x-3 gap-y-1 bg-white/5 px-3 py-2 text-xs text-ink-soft">
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
                className="ml-1 rounded border border-lime/30 px-1.5 py-0.5 text-[10px] text-lime hover:bg-lime/10"
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
