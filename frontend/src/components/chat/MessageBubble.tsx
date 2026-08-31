import dynamic from "next/dynamic";
import type { Msg } from "@/types/api";
import { InsightCard } from "./InsightCard";
import { PlanCard } from "./PlanCard";
import { ReportCard } from "./ReportCard";
import { StepsCard } from "./StepsCard";

const SpotsMap = dynamic(() => import("./SpotsMap").then((m) => m.SpotsMap), { ssr: false });

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
    <div className={isUser ? "chat-msg flex justify-end" : "chat-msg flex items-start justify-start gap-2"}>
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-lime text-sm font-bold text-[#17110a]">
          L
        </div>
      )}
      <div
        className={
          isUser
            ? "max-w-[85%] rounded-2xl rounded-br-md bg-lime px-4 py-2.5 text-sm leading-6 text-[#17110a]"
            : "max-w-[92%] rounded-2xl rounded-bl-md bg-white/10 px-4 py-3 text-sm leading-6 text-white ring-1 ring-white/10"
        }
      >
        {msg.content && <p className="whitespace-pre-wrap">{msg.content}</p>}
        {msg.error && <p className="mt-1 text-orange-300">{msg.error}</p>}
        {loading && !isUser && !msg.content && !msg.error && (
          <p className="text-white/55">正在整理条件与方案…</p>
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
        {msg.spots && <SpotsMap spots={msg.spots} />}

        {msg.quick_options && (
          <div className="mt-3 flex flex-wrap gap-2">
            {msg.quick_options.map((q) => (
              <button
                key={q}
                onClick={() => onSend(q)}
                disabled={loading}
                className="rounded-full border border-lime/40 bg-lime/10 px-3 py-1 text-xs font-semibold text-lime disabled:opacity-50"
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
