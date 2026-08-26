"use client";

import type { FishScore } from "@/types/api";

function color(score: number): string {
  if (score >= 70) return "#62a765";
  if (score >= 50) return "#d9a441";
  return "#e85d38";
}

export function FishScoreChart({
  scores,
  onAsk,
}: {
  scores: FishScore[];
  onAsk?: (hour: number) => void;
}) {
  const nowHour = new Date().getHours();

  return (
    <div className="lure-fishchart">
      <div className="lure-fishchart-head">
        <strong>逐小时鱼口参考（点击柱子问老付）</strong>
        <div className="lure-fishchart-legend">
          <span>
            <i style={{ background: "#62a765" }} /> 好
          </span>
          <span>
            <i style={{ background: "#d9a441" }} /> 一般
          </span>
          <span>
            <i style={{ background: "#e85d38" }} /> 差
          </span>
        </div>
      </div>

      <div className="lure-fishchart-bars">
        {scores.map((s) => {
          const isNow = parseInt(s.hour, 10) === nowHour;
          return (
            <div
              key={s.hour}
              className="lure-fishchart-col"
              onClick={() => onAsk?.(parseInt(s.hour, 10))}
              title={`${s.hour}:00 ${s.condition} ${s.temp}℃ · 鱼口 ${s.score}（点击问老付）`}
            >
              <div className="lure-fishchart-bar-wrap">
                <div
                  className="lure-fishchart-bar"
                  style={{
                    height: `${Math.max(s.score, 8)}%`,
                    background: color(s.score),
                  }}
                />
              </div>
              <span className={isNow ? "is-now" : ""}>{s.hour}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
