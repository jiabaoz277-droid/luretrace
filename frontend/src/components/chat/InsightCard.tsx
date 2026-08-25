import type { InsightStats } from "@/types/api";

export function InsightCard({ insight }: { insight: InsightStats }) {
  return (
    <div className="mt-3 rounded-xl border border-line bg-surface p-3 text-xs text-ink">
      <p className="mb-1.5 font-semibold text-daiwa">📊 我的规律（共 {insight.total} 次战报）</p>
      {Object.keys(insight.result_dist).length > 0 && (
        <p className="text-ink-soft">
          结果分布：
          {Object.entries(insight.result_dist)
            .map(([k, v]) => `${k} ${v} 次`)
            .join(" · ")}
        </p>
      )}
      {insight.top_species?.length > 0 && (
        <p className="text-ink-soft">
          常钓目标鱼：
          {insight.top_species.map((s) => `${s.species}（${s.count}次）`).join(" · ")}
        </p>
      )}
    </div>
  );
}
