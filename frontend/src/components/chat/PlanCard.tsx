import { History } from "lucide-react";
import type { Plan } from "@/types/api";

const CONCLUSION_TEXT: Record<Plan["conclusion"], string> = {
  go: "建议去",
  conditional: "可去但窗口短",
  no_go: "不建议",
};

const CONCLUSION_CLS: Record<Plan["conclusion"], string> = {
  go: "bg-daiwa/10 text-daiwa",
  conditional: "bg-amber-100 text-amber-700",
  no_go: "bg-accent/10 text-accent",
};

const CONFIDENCE_TEXT = { high: "高", mid: "中", low: "低" } as const;

const CONDITION_BAND_TEXT: Record<"good" | "fair" | "poor", string> = {
  good: "较适合",
  fair: "可尝试",
  poor: "不理想",
};

function dataText(c?: number): string {
  if (c == null) return "数据未知";
  if (c >= 0.75) return "数据较完整";
  if (c >= 0.5) return "数据一般";
  return "数据不足";
}

export function PlanCard({ plan }: { plan: Plan }) {
  const d = plan.plan_detail || {};
  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-line bg-surface">
      {/* 第一层：结论 + 信心/数据 */}
      <div className="flex items-center justify-between border-b border-line bg-paper px-3 py-2">
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${CONCLUSION_CLS[plan.conclusion]}`}>
          {CONCLUSION_TEXT[plan.conclusion]}
        </span>
        <span className="text-xs text-ink-soft">
          信心{CONFIDENCE_TEXT[plan.confidence]} · {dataText(plan.data_completeness)}
        </span>
      </div>

      {/* 第二层：最佳窗口 + 方案动作 */}
      <dl className="space-y-1.5 p-3 text-xs text-ink">
        {plan.best_window && (
          <Row
            label="最佳窗口"
            value={plan.best_window + (plan.backup_window ? `（备选 ${plan.backup_window}）` : "")}
          />
        )}
        {plan.location && <Row label="地点" value={plan.location} />}
        {plan.target_species && <Row label="目标鱼" value={plan.target_species} />}
        {d.spot_type && <Row label="标点" value={d.spot_type} />}
        {d.water_layer && <Row label="水层" value={d.water_layer} />}
        {d.primary_lure && (
          <Row label="拟饵" value={`${d.primary_lure}${d.weight_color ? `（${d.weight_color}）` : ""}`} />
        )}
        {d.action && <Row label="手法" value={d.action} />}
      </dl>

      {/* 条件档位（替代"辅助分"，不制造虚假精确度） */}
      <p className="border-t border-line px-3 py-2 text-xs text-ink-soft">
        条件：{CONDITION_BAND_TEXT[plan.condition_band || "fair"]}
        {plan.condition_score_range
          ? `（${plan.condition_score_range[0]}–${plan.condition_score_range[1]}）`
          : ""}
        。该指数仅基于天气与时段估算，不代表实际鱼口。
      </p>

      {/* 为什么 + 风险/安全 */}
      {plan.factors?.length > 0 && (
        <p className="px-3 py-1 text-xs text-ink-soft">
          依据：{plan.factors.slice(0, 3).join("；")}
        </p>
      )}
      {plan.risks?.length > 0 && (
        <p className="px-3 pb-1 text-xs text-amber-700">注意：{plan.risks.join("；")}</p>
      )}
      {plan.safety?.length > 0 && (
        <p className="px-3 pb-1 text-xs font-semibold text-accent">安全：{plan.safety.join("；")}</p>
      )}
      {plan.history_note && (
        <p className="flex items-start gap-1 px-3 pb-2 text-xs text-daiwa">
          <History className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {plan.history_note}
        </p>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="w-14 shrink-0 text-ink-soft">{label}</dt>
      <dd className="min-w-0 flex-1">{value}</dd>
    </div>
  );
}
