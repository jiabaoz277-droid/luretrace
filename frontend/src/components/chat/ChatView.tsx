"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, MapPin } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { Msg } from "@/types/api";
import { MessageBubble } from "./MessageBubble";

const QUICK_QUESTIONS = [
  "今天值得去吗",
  "到水边没口",
  "明早杭州周边两小时打翘嘴",
  "记一下今天的战报",
  "我的规律",
];

export function ChatView({
  messages,
  loading,
  onSend,
  onLocated,
}: {
  messages: Msg[];
  loading: boolean;
  onSend: (text: string, context?: { lat?: number; lon?: number }) => void;
  onLocated?: (name: string) => void;
}) {
  const [input, setInput] = useState("");
  const [locating, setLocating] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function locate() {
    if (!("geolocation" in navigator)) {
      alert("当前浏览器不支持定位，请在下方手动输入城市");
      return;
    }
    if (!window.isSecureContext) {
      alert("当前不是 HTTPS 安全连接，浏览器禁止定位。请手动输入城市或水域。");
      return;
    }
    setLocating(true);
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          timeout: 15000,
          maximumAge: 300000, // 5 分钟内可用缓存位置，提升成功率
          enableHighAccuracy: false, // 网络定位即可，更快更稳
        });
      });
      const { latitude, longitude } = pos.coords;
      const res = await apiFetch(`/api/v1/geo/reverse?lat=${latitude}&lon=${longitude}`);
      const data = await res.json();
      if (data.name) {
        // 对话框里明确显示定位结果，并同步给底部天气面板
        onSend(`📍 我的位置：${data.name}`, { lat: latitude, lon: longitude });
        onLocated?.(data.name);
      } else {
        alert("已获取坐标，但没解析出城市，请手动输入城市");
      }
    } catch (err) {
      let reason = "无法获取位置，请手动输入城市或水域";
      if (err && typeof err === "object" && "code" in err) {
        const code = (err as GeolocationPositionError).code;
        if (code === 1) reason = "定位权限被拒绝：请在浏览器设置里允许定位，或直接输入城市";
        else if (code === 3) reason = "定位超时：请重试，或直接输入城市";
      }
      alert(reason);
    } finally {
      setLocating(false);
    }
  }

  return (
    <>
      <main className="flex-1 space-y-3 overflow-y-auto px-2 py-4 sm:px-3">
        {messages.length === 0 && (
          <div className="rounded-2xl border border-white/10 bg-white/8 p-4 text-sm text-white/65">
            <div className="mb-2 flex items-center gap-2">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-lime text-sm font-bold text-daiwa">
                付
              </div>
              <p className="font-semibold text-white">今天想怎么钓？</p>
            </div>
            <p className="leading-6">时间、地点、对象鱼，知道多少说多少。例：明早杭州周边两小时，想打翘嘴。</p>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} msg={m} loading={loading} onSend={onSend} />
        ))}
        <div ref={bottomRef} />
      </main>

      <footer className="border-t border-white/10 bg-daiwa px-1 pt-3">
        <div className="mb-2 flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none]">
          <button
            type="button"
            onClick={locate}
            disabled={loading || locating}
            className="flex shrink-0 items-center gap-1.5 rounded-full border border-lime/45 bg-lime/10 px-3 py-1.5 text-[11px] font-semibold text-lime disabled:opacity-50"
          >
            <MapPin className="h-3.5 w-3.5" />
            {locating ? "定位中…" : "当前位置"}
          </button>
          {QUICK_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => onSend(q)}
              disabled={loading}
              className="shrink-0 rounded-full border border-white/15 bg-white/6 px-3 py-1.5 text-[11px] font-medium text-white/75 hover:border-lime/55 hover:text-lime disabled:opacity-50"
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
          className="flex min-h-14 items-center gap-2 rounded-2xl bg-white p-1.5 pl-4 shadow-lg shadow-black/10"
        >
          <label className="sr-only" htmlFor="chat-input">
            输入出钓问题
          </label>
          <input
            id="chat-input"
            aria-describedby="chat-hint"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="例：明早杭州周边两小时，想打翘嘴"
            className="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-soft/60"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-lime text-daiwa disabled:opacity-45"
            aria-label="发送"
          >
            <ArrowUp className="h-5 w-5" />
          </button>
        </form>
      </footer>
    </>
  );
}
