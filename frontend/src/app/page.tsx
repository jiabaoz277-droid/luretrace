"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8003`
    : "http://localhost:8003");

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
  history_note?: string | null;
};

type Step = { action: string; duration: string; upgrade: string };

type Report = {
  id: number;
  result_type: string;
  result_label: string;
  species?: string | null;
  count?: number | null;
  lure?: string | null;
  review?: string | null;
  review_confirmed: boolean;
};

type InsightStats = {
  total: number;
  result_dist: Record<string, number>;
  top_species: { species: string; count: number }[];
  recent: Report[];
};

type Msg = {
  role: "user" | "assistant";
  content: string;
  plan?: Plan | null;
  missing?: string[];
  steps?: Step[];
  report?: Report | null;
  quick_options?: string[];
  insight?: InsightStats | null;
  error?: string;
};

const QUICK_QUESTIONS = [
  "今天值得去吗",
  "明早杭州周边两小时打翘嘴",
  "到水边没口",
  "记一下今天的战报",
  "我的规律",
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
  const [showProfile, setShowProfile] = useState(false);
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

  const send = useCallback(
    async (text: string) => {
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
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
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
                steps: p.steps ?? undefined,
                report: p.report ?? null,
                quick_options: p.quick_options ?? undefined,
                insight: p.insight ?? null,
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
    },
    [loading]
  );

  return (
    <div className="mx-auto flex h-dvh max-w-md flex-col bg-[#f5f7f9]">
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">路亚问问</h1>
          <p className="text-xs text-gray-500">对话式出钓决策助手 · 第 2 阶段</p>
        </div>
        <button
          onClick={() => setShowProfile(true)}
          className="rounded-full border border-gray-300 px-3 py-1 text-sm text-gray-700"
        >
          我的
        </button>
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
              {m.steps && <StepsCard steps={m.steps} />}
              {m.report && <ReportCard report={m.report} onConfirm={() => send("确认")} onCancel={() => send("取消")} />}
              {m.insight && <InsightCard insight={m.insight} />}
              {m.quick_options && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {m.quick_options.map((q) => (
                    <button
                      key={q}
                      onClick={() => send(q)}
                      disabled={loading}
                      className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs text-blue-600 disabled:opacity-50"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}
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

      {showProfile && <ProfilePanel onClose={() => setShowProfile(false)} />}
    </div>
  );
}

function PlanCard({ plan }: { plan: Plan }) {
  const d = plan.plan_detail || {};
  return (
    <div className="mt-3 rounded-xl border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700">
      <div className="mb-2 flex items-center justify-between">
        <span className={`rounded-full px-2 py-0.5 font-medium ${CONCLUSION_COLOR[plan.conclusion]}`}>
          {CONCLUSION_TEXT[plan.conclusion]} · 信心{plan.confidence === "high" ? "高" : plan.confidence === "mid" ? "中" : "低"}
        </span>
        <span className="text-gray-500">辅助分 {plan.score}</span>
      </div>
      <dl className="space-y-1">
        {plan.best_window && <Row label="最佳窗口" value={plan.best_window + (plan.backup_window ? `（备选 ${plan.backup_window}）` : "")} />}
        {plan.location && <Row label="地点" value={plan.location} />}
        {plan.target_species && <Row label="目标鱼" value={plan.target_species} />}
        {d.spot_type && <Row label="标点" value={d.spot_type} />}
        {d.water_layer && <Row label="水层" value={d.water_layer} />}
        {d.primary_lure && <Row label="拟饵" value={`${d.primary_lure}${d.weight_color ? `（${d.weight_color}）` : ""}`} />}
        {d.action && <Row label="手法" value={d.action} />}
      </dl>
      {plan.factors?.length > 0 && <p className="mt-2 text-gray-500">依据：{plan.factors.slice(0, 3).join("；")}</p>}
      {plan.risks?.length > 0 && <p className="mt-1 text-amber-600">注意：{plan.risks.join("；")}</p>}
      {plan.safety?.length > 0 && <p className="mt-1 font-medium text-red-600">安全：{plan.safety.join("；")}</p>}
      {plan.history_note && <p className="mt-1 text-blue-600">📖 {plan.history_note}</p>}
    </div>
  );
}

function StepsCard({ steps }: { steps: Step[] }) {
  return (
    <div className="mt-3 rounded-xl border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700">
      {steps.map((s, i) => (
        <div key={i} className="mb-2 last:mb-0">
          <p className="font-medium">
            {i + 1}. {s.action}
          </p>
          <p className="text-gray-500">观察 {s.duration}{s.upgrade !== "—" ? `；${s.upgrade}` : ""}</p>
        </div>
      ))}
    </div>
  );
}

function ReportCard({ report, onConfirm, onCancel }: { report: Report; onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="mt-3 rounded-xl border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700">
      <div className="mb-1 flex items-center justify-between">
        <span className="rounded-full bg-blue-100 px-2 py-0.5 font-medium text-blue-700">
          战报 · {report.result_label}
        </span>
        {report.review_confirmed ? (
          <span className="text-emerald-600">已写入历史</span>
        ) : (
          <span className="text-gray-400">待确认</span>
        )}
      </div>
      {report.species && <p>目标鱼：{report.species}</p>}
      {report.count != null && <p>数量：{report.count}</p>}
      {!report.review_confirmed && (
        <div className="mt-2 flex gap-2">
          <button onClick={onConfirm} className="rounded-full bg-blue-600 px-3 py-1 text-white">
            确认写入
          </button>
          <button onClick={onCancel} className="rounded-full border border-gray-300 px-3 py-1 text-gray-600">
            取消
          </button>
        </div>
      )}
    </div>
  );
}

function InsightCard({ insight }: { insight: InsightStats }) {
  return (
    <div className="mt-3 rounded-xl border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700">
      <p className="mb-1 font-medium">📊 我的规律（共 {insight.total} 次战报）</p>
      {Object.keys(insight.result_dist).length > 0 && (
        <p className="text-gray-500">
          结果分布：{Object.entries(insight.result_dist).map(([k, v]) => `${k}${v}次`).join("、")}
        </p>
      )}
      {insight.top_species?.length > 0 && (
        <p className="text-gray-500">
          常钓目标鱼：{insight.top_species.map((s) => `${s.species}(${s.count}次)`).join("、")}
        </p>
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

function ProfilePanel({ onClose }: { onClose: () => void }) {
  const [lures, setLures] = useState("");
  const [radius, setRadius] = useState("");
  const [noNight, setNoNight] = useState(false);
  const [noWading, setNoWading] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/profile`)
      .then((r) => r.json())
      .then((p) => {
        setLures((p.lures || []).join("、"));
        setRadius(p.max_travel_radius || "");
        setNoNight((p.constraints || []).includes("不夜钓"));
        setNoWading((p.constraints || []).includes("不涉水"));
      })
      .catch(() => {});
  }, []);

  async function save() {
    const constraints: string[] = [];
    if (noNight) constraints.push("不夜钓");
    if (noWading) constraints.push("不涉水");
    await fetch(`${API_BASE}/api/v1/profile`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lures: lures.split(/[,，、]/).map((s) => s.trim()).filter(Boolean),
        max_travel_radius: radius || null,
        constraints,
      }),
    });
    setSaved(true);
    setTimeout(onClose, 800);
  }

  return (
    <div className="fixed inset-0 z-10 flex items-end justify-center bg-black/30" onClick={onClose}>
      <div className="w-full max-w-md rounded-t-2xl bg-white p-5" onClick={(e) => e.stopPropagation()}>
        <h2 className="mb-3 text-base font-semibold">我的装备与偏好</h2>
        <label className="mb-3 block text-sm">
          <span className="text-gray-600">常用拟饵（逗号分隔）</span>
          <input
            value={lures}
            onChange={(e) => setLures(e.target.value)}
            placeholder="如：7g亮片、米诺"
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="mb-3 block text-sm">
          <span className="text-gray-600">最大车程</span>
          <input
            value={radius}
            onChange={(e) => setRadius(e.target.value)}
            placeholder="如：40分钟"
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </label>
        <div className="mb-4 flex gap-6 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={noNight} onChange={(e) => setNoNight(e.target.checked)} />
            不夜钓
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={noWading} onChange={(e) => setNoWading(e.target.checked)} />
            不涉水
          </label>
        </div>
        <div className="flex gap-3">
          <button onClick={save} className="flex-1 rounded-full bg-blue-600 py-2 text-sm font-medium text-white">
            {saved ? "已保存 ✓" : "保存"}
          </button>
          <button onClick={onClose} className="rounded-full border border-gray-300 px-5 py-2 text-sm text-gray-600">
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
