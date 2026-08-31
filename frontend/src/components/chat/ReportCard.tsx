import type { Report } from "@/types/api";

export function ReportCard({
  report,
  onConfirm,
  onCancel,
}: {
  report: Report;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-ink">
      <div className="mb-1 flex items-center justify-between">
        <span className="rounded-full bg-lime/15 px-2 py-0.5 font-semibold text-lime">
          战报 · {report.result_label}
        </span>
        {report.review_confirmed ? (
          <span className="text-emerald-400">已写入历史</span>
        ) : (
          <span className="text-ink-soft">待确认</span>
        )}
      </div>
      {report.species && <p className="mt-1">目标鱼：{report.species}</p>}
      {report.count != null && <p>数量：{report.count}</p>}
      {!report.review_confirmed && (
        <div className="mt-2 flex gap-2">
          <button
            onClick={onConfirm}
            className="rounded-full bg-lime px-3 py-1 font-semibold text-[#17110a]"
          >
            确认写入
          </button>
          <button
            onClick={onCancel}
            className="rounded-full border border-white/15 px-3 py-1 text-ink-soft"
          >
            取消
          </button>
        </div>
      )}
    </div>
  );
}
