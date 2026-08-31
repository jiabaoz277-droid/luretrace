import { BarChart3 } from "lucide-react";
import type { InsightStats } from "@/types/api";

export function InsightCard({ insight }: { insight: InsightStats }) {
  return (
    <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-ink">
      <p className="mb-1.5 flex items-center gap-1.5 font-semibold text-lime">
        <BarChart3 className="h-4 w-4" />
        我的规律（共 {insight.total} 次战报）
      </p>
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
