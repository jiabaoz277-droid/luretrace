"use client";

import { useEffect, useRef, useState } from "react";
import type { Msg } from "@/types/api";
import { MessageBubble } from "./MessageBubble";

const QUICK_QUESTIONS = [
  "今天值得去吗",
  "明早杭州周边两小时打翘嘴",
  "到水边没口",
  "记一下今天的战报",
  "我的规律",
];

export function ChatView({
  messages,
  loading,
  onSend,
}: {
  messages: Msg[];
  loading: boolean;
  onSend: (text: string) => void;
}) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <>
      <main className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="rounded-xl border border-line bg-surface p-4 text-sm text-ink-soft">
            <p className="mb-1 font-semibold text-ink">👋 告诉我你的出钓计划</p>
            <p>例：明早杭州周边两小时，想打翘嘴</p>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} msg={m} loading={loading} onSend={onSend} />
        ))}
        <div ref={bottomRef} />
      </main>

      <footer className="border-t border-line bg-surface p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
        <div className="mb-2 flex gap-2 overflow-x-auto pb-1">
          {QUICK_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => onSend(q)}
              disabled={loading}
              className="shrink-0 rounded-full border border-daiwa/30 bg-daiwa/5 px-3 py-1 text-xs font-medium text-daiwa disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (input.trim()) {
              onSend(input);
              setInput("");
            }
          }}
          className="flex items-center gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="你准备什么时候、去哪里、打什么鱼？"
            className="min-h-11 flex-1 rounded-full border border-line bg-paper px-4 py-2 text-sm text-ink outline-none focus:border-daiwa"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="min-h-11 rounded-full bg-daiwa px-5 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            发送
          </button>
        </form>
      </footer>
    </>
  );
}
