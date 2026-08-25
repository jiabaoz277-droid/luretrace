import type { Msg } from "@/types/api";
import { InsightCard } from "./InsightCard";
import { PlanCard } from "./PlanCard";
import { ReportCard } from "./ReportCard";
import { StepsCard } from "./StepsCard";

export function MessageBubble({
  msg,
  loading,
  onSend,
}: {
  msg: Msg;
  loading: boolean;
  onSend: (text: string) => void;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={isUser ? "flex justify-end" : "flex justify-start"}>
      <div
        className={
          isUser
            ? "max-w-[85%] rounded-2xl bg-daiwa px-4 py-2 text-sm text-white"
            : "max-w-[92%] rounded-2xl bg-surface px-4 py-3 text-sm text-ink shadow-sm ring-1 ring-line/60"
        }
      >
        {msg.content && <p className="whitespace-pre-wrap">{msg.content}</p>}
        {msg.error && <p className="mt-1 text-accent">{msg.error}</p>}
        {loading && !isUser && !msg.content && !msg.error && (
          <p className="text-ink-soft">正在思考…</p>
        )}

        {msg.plan && <PlanCard plan={msg.plan} />}
        {msg.steps && <StepsCard steps={msg.steps} />}
        {msg.report && (
          <ReportCard
            report={msg.report}
            onConfirm={() => onSend("确认")}
            onCancel={() => onSend("取消")}
          />
        )}
        {msg.insight && <InsightCard insight={msg.insight} />}

        {msg.quick_options && (
          <div className="mt-2 flex flex-wrap gap-2">
            {msg.quick_options.map((q) => (
              <button
                key={q}
                onClick={() => onSend(q)}
                disabled={loading}
                className="rounded-full border border-daiwa/30 bg-daiwa/5 px-3 py-1 text-xs font-medium text-daiwa disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
