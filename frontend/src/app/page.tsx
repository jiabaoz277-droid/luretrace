"use client";

import { useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8003";

type PlanDetail = {
  spot_type?: string | null;
  water_layer?: string | null;
  primary_lure?: string | null;
  backup_lure?: string | null;
  weight_color?: string | null;
  action?: string | null;
  adjust_condition?: string | null;
};

type Plan = {
  version: number;
  location?: string | null;
  time_window?: string | null;
  target_species?: string | null;
  travel_radius?: string | null;
  conclusion: "go" | "conditional" | "no_go";
  confidence: "high" | "mid" | "low";
  score: number;
  best_window?: string | null;
  backup_window?: string | null;
  factors: string[];
  plan_detail: PlanDetail;
  risks: string[];
  safety: string[];
  data_basis: Record<string, unknown>;
};

type Msg = {
  role: "user" | "assistant";
  content: string;
  plan?: Plan | null;
  missing?: string[];
  error?: string;
};

const QUICK_QUESTIONS = [
  "今天值得去吗",
  "明早杭州周边两小时打翘嘴",
  "附近打翘嘴",
  "雷暴天能去吗",
];

const CONCLUSION_TEXT: Record<Plan["conclusion"], string> = {
  go: "建议去",
  conditional: "可去但窗口短",
  no_go: "不建议",
};

const CONCLUSION_COLOR: Record<Plan["conclusion"], string> = {
  go: "bg-emerald-100 text-emerald-700",
  conditional: "bg-amber-100 text-amber-700",
  no_go: "bg-red-100 text-red-700",
};

export default function Home() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const sessionRef = useRef<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function updateLastAssistant(updater: (m: Msg) => Msg) {
    setMessages((prev) => {
      const next = [...prev];
      for (let i = next.length - 1; i >= 0; i--) {
        if (next[i].role === "assistant") {
          next[i] = updater(next[i]);
          break;
        }
      }
      return next;
    });
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || loading) return;
    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: message },
      { role: "assistant", content: "" },
    ]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: sessionRef.current }),
      });
      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let streaming = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx: number;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const block = buffer.slice(0, idx).trim();
          buffer = buffer.slice(idx + 2);
          if (!block.startsWith("data: ")) continue;
          const data = JSON.parse(block.slice(6));

          if (data.session_id) sessionRef.current = data.session_id;

          if (data.type === "chunk") {
            streaming = true;
            updateLastAssistant((m) => ({ ...m, content: m.content + data.content }));
          } else if (data.type === "done") {
            const p = data.payload;
            updateLastAssistant((m) => ({
              ...m,
              content: p.reply || m.content,
              plan: p.plan ?? null,
              missing: p.missing ?? undefined,
            }));
          } else if (data.type === "error") {
            updateLastAssistant((m) => ({
              ...m,
              error: data.error?.message || "出错了，请稍后重试",
            }));
          }
        }
      }
      if (!streaming) {
        updateLastAssistant((m) => ({
          ...m,
          content: m.content || "（无响应，请稍后重试）",
        }));
      }
    } catch {
      updateLastAssistant((m) => ({
        ...m,
        error: "无法连接服务，请确认后端已启动（端口 8003）",
      }));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex h-dvh max-w-md flex-col bg-[#f5f7f9]">
      <header className="border-b border-gray-200 bg-white px-4 py-3">
        <h1 className="text-lg font-semibold text-gray-900">路亚问问</h1>
        <p className="text-xs text-gray-500">对话式出钓决策助手 · MVP</p>
      </header>

      <main className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="rounded-xl bg-white p-4 text-sm text-gray-600 shadow-sm">
            <p className="mb-2 font-medium text-gray-800">👋 告诉我你的出钓计划</p>
            <p>例：明早杭州周边两小时，想打翘嘴</p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={
                m.role === "user"
                  ? "max-w-[85%] rounded-2xl bg-blue-600 px-4 py-2 text-sm text-white"
                  : "max-w-[92%] rounded-2xl bg-white px-4 py-3 text-sm text-gray-800 shadow-sm"
              }
            >
              {m.content && <p className="whitespace-pre-wrap">{m.content}</p>}
              {m.error && <p className="mt-1 text-red-500">{m.error}</p>}
              {loading && m.role === "assistant" && !m.content && !m.error && (
                <p className="text-gray-400">正在思考…</p>
              )}
              {m.plan && <PlanCard plan={m.plan} />}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </main>

      <footer className="border-t border-gray-200 bg-white p-3">
        <div className="mb-2 flex gap-2 overflow-x-auto pb-1">
          {QUICK_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => send(q)}
              disabled={loading}
              className="shrink-0 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs text-blue-600 disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex items-center gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="你准备什么时候、去哪里、打什么鱼？"
            className="flex-1 rounded-full border border-gray-300 px-4 py-2 text-sm outline-none focus:border-blue-400"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-full bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            发送
          </button>
        </form>
      </footer>
    </div>
  );
}

function PlanCard({ plan }: { plan: Plan }) {
  const d = plan.plan_detail || {};
  return (
    <div className="mt-3 rounded-xl border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700">
      <div className="mb-2 flex items-center justify-between">
        <span
          className={`rounded-full px-2 py-0.5 font-medium ${CONCLUSION_COLOR[plan.conclusion]}`}
        >
          {CONCLUSION_TEXT[plan.conclusion]} · 信心{plan.confidence === "high" ? "高" : plan.confidence === "mid" ? "中" : "低"}
        </span>
        <span className="text-gray-500">辅助分 {plan.score}</span>
      </div>

      <dl className="space-y-1">
        {plan.best_window && (
          <Row label="最佳窗口" value={plan.best_window + (plan.backup_window ? `（备选 ${plan.backup_window}）` : "")} />
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

      {plan.factors?.length > 0 && (
        <p className="mt-2 text-gray-500">依据：{plan.factors.slice(0, 3).join("；")}</p>
      )}
      {plan.risks?.length > 0 && (
        <p className="mt-1 text-amber-600">注意：{plan.risks.join("；")}</p>
      )}
      {plan.safety?.length > 0 && (
        <p className="mt-1 font-medium text-red-600">安全：{plan.safety.join("；")}</p>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="w-14 shrink-0 text-gray-400">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
