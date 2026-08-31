"use client";

import Image from "next/image";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

export function LoginView({ onLogin }: { onLogin: () => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [shake, setShake] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = code.trim();
    if (!trimmed || loading || success) {
      if (!trimmed) {
        setError("请输入邀请码");
        setShake(false);
        window.requestAnimationFrame(() => setShake(true));
      }
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ code: trimmed }),
      });
      const data = await response.json().catch(() => null);
      if (response.ok && data?.ok) {
        setSuccess(true);
        window.setTimeout(onLogin, 1900);
      } else {
        setError(data?.detail?.message || "邀请码不正确");
        setShake(false);
        window.requestAnimationFrame(() => setShake(true));
      }
    } catch {
      setError("网络异常，请稍后重试");
      setShake(false);
      window.requestAnimationFrame(() => setShake(true));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className={`login-cinematic${success ? " is-reeling" : ""}`}>
      <div className="login-cinematic-bg" aria-hidden="true" />
      <div className="login-cinematic-overlay" aria-hidden="true" />
      <div className={`login-ripple${success ? " is-active" : ""}`} aria-hidden="true" />

      <section className="login-fish-scene" aria-label="路迹">
        <div className="login-fish-wrap">
          <Image className="login-fish-image" src="/login-fish.png" alt="跃出水面的路亚鱼" width={399} height={400} priority sizes="(max-width: 480px) 280px, 360px" />
          <div className="login-fish-brand" aria-hidden="true">
            <strong>路迹</strong>
            <span>LURETRACE</span>
          </div>
        </div>
      </section>

      <form className={`login-access${shake ? " is-shaking" : ""}`} onSubmit={submit} onAnimationEnd={() => setShake(false)}>
        <p>输入邀请码，收线上岸</p>
        <div className="login-access-row">
        <label className="sr-only" htmlFor="invite-code">邀请码</label>
          <input id="invite-code" type="password" value={code} onChange={(event) => { setCode(event.target.value); setError(""); }} placeholder="请输入邀请码" autoFocus maxLength={128} autoComplete="one-time-code" aria-invalid={Boolean(error)} aria-describedby={error ? "login-error" : undefined} />
          <button type="submit" disabled={loading || success}>{loading ? "验证中" : "进入"}</button>
        </div>
        <div className="login-access-meta">
          <span id="login-error" role="alert">{error}</span>
          <small>仅限受邀用户 · 数据只用于生成你的方案</small>
        </div>
      </form>

      <div className={`login-success${success ? " is-visible" : ""}`} aria-live="polite">
        <svg viewBox="0 0 60 60" fill="none" aria-hidden="true">
          <path d="M10 30Q20 12 38 14Q50 15 52 30Q50 45 38 46Q20 48 10 30Z" fill="currentColor" />
          <path d="m52 30 6-8-2 8 2 8Z" fill="currentColor" opacity=".6" />
          <circle cx="20" cy="26" r="2.5" fill="#182129" />
        </svg>
        <strong>祝您爆护</strong>
        <span>LURETRACE · 路亚决策助手</span>
      </div>
    </main>
  );
}
