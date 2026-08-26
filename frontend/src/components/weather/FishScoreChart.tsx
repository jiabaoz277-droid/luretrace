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
        <strong>逐小时出钓条件（点击查看原因）</strong>
        <div className="lure-fishchart-legend">
          <span>
            <i style={{ background: "#62a765" }} /> 较适合
          </span>
          <span>
            <i style={{ background: "#d9a441" }} /> 可尝试
          </span>
          <span>
            <i style={{ background: "#e85d38" }} /> 不理想
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
              title={`${s.hour}:00 ${s.condition} ${s.temp}℃ · 条件 ${s.score}（点击问老付）`}
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
      <p className="lure-fishchart-note">
        该指数仅根据天气、时段和目标鱼习性估算，不包含实时水温、水位和现场鱼情，不代表必然有口。
      </p>
    </div>
  );
}
