"use client";

import { useState } from "react";
import { apiFetch, setToken } from "@/lib/api";

export function LoginView({ onLogin }: { onLogin: () => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = code.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError("");
    try {
      const res = await apiFetch("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ code: trimmed }),
      });
      const data = await res.json().catch(() => null);
      if (res.ok && data?.token) {
        setToken(data.token);
        onLogin();
      } else {
        setError(data?.detail?.message || "邀请码不正确");
      }
    } catch {
      setError("网络异常，请稍后重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-daiwa px-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-3xl bg-white p-8 shadow-2xl shadow-black/30"
      >
        <div className="mb-6 flex flex-col items-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-lime text-2xl font-bold text-daiwa">
            付
          </div>
          <h1 className="mt-4 text-xl font-bold text-ink">路亚问问</h1>
          <p className="mt-1 text-sm text-ink-soft">输入邀请码开始使用</p>
        </div>

        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="邀请码"
          autoFocus
          maxLength={128}
          className="min-h-12 w-full rounded-xl border border-line bg-paper px-4 text-base outline-none focus:border-daiwa"
        />

        {error && <p className="mt-2 text-sm text-accent">{error}</p>}

        <button
          type="submit"
          disabled={loading || !code.trim()}
          className="mt-4 min-h-12 w-full rounded-xl bg-daiwa text-base font-semibold text-white disabled:opacity-50"
        >
          {loading ? "登录中…" : "进入"}
        </button>
      </form>
    </main>
  );
}
