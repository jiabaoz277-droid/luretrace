"use client";

import { useCallback, useRef, useState } from "react";
import type { Msg } from "@/types/api";
import { API_BASE } from "@/lib/api";
import { parseSSEEvent } from "@/lib/sse";

/** 会话状态 + SSE 流式对话。 */
export function useChat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(false);
  const sessionRef = useRef<string | null>(null);

  const updateLastAssistant = useCallback((updater: (m: Msg) => Msg) => {
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
  }, []);

  const send = useCallback(
    async (text: string) => {
      const message = text.trim();
      if (!message || loading) return;
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
            const line = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            const ev = parseSSEEvent(line);
            if (!ev) continue;

            if (ev.type === "chunk") {
              streaming = true;
              if (ev.session_id) sessionRef.current = ev.session_id;
              updateLastAssistant((m) => ({ ...m, content: m.content + ev.content }));
            } else if (ev.type === "done") {
              if (ev.session_id) sessionRef.current = ev.session_id;
              const p = ev.payload;
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
            } else if (ev.type === "error") {
              updateLastAssistant((m) => ({
                ...m,
                error: ev.error?.message || "出错了，请稍后重试",
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
    [loading, updateLastAssistant]
  );

  return { messages, loading, send };
}
