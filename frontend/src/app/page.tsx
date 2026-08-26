"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { ChatView } from "@/components/chat/ChatView";
import { ProfilePanel } from "@/components/profile/ProfilePanel";
import { LivePanel } from "@/components/weather/LivePanel";
import { WeatherDashboard } from "@/components/weather/WeatherDashboard";
import { LoginView } from "@/components/LoginView";
import { getToken } from "@/lib/api";
import { useChat } from "@/hooks/useChat";

export default function Home() {
  const { messages, loading, send } = useChat();
  const [showProfile, setShowProfile] = useState(false);
  const [showWeather, setShowWeather] = useState(false);
  const [userLocation, setUserLocation] = useState<string | null>(null);
  const [authed, setAuthed] = useState(false);
  const [ready, setReady] = useState(false);

  // 从最近方案卡提取目标鱼种与车程限制，供底部钓点推荐使用
  const latestPlan = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].plan) return messages[i].plan;
    }
    return null;
  }, [messages]);
  const species = latestPlan?.target_species ?? undefined;
  const travelMinutes = useMemo(() => {
    const r = latestPlan?.travel_radius;
    if (!r) return undefined;
    const h = r.match(/(\d+)\s*小时/);
    if (h) return parseInt(h[1], 10) * 60;
    const m = r.match(/(\d+)\s*分钟/);
    if (m) return parseInt(m[1], 10);
    return undefined;
  }, [latestPlan]);

  useEffect(() => {
    setAuthed(!!getToken());
    setReady(true);
    const onUnauthorized = () => setAuthed(false);
    window.addEventListener("lure:unauthorized", onUnauthorized);
    return () => window.removeEventListener("lure:unauthorized", onUnauthorized);
  }, []);

  if (!ready) return null;
  if (!authed) return <LoginView onLogin={() => setAuthed(true)} />;

  return (
    <main className="lure-app-shell">
      <header className="lure-topbar">
        <div className="lure-brand" aria-label="路亚问问">
          <span className="lure-brand-mark">付</span>
          <div>
            <h1>路亚问问</h1>
            <small>LURE DECISION ASSISTANT</small>
          </div>
        </div>
        <nav className="lure-nav" aria-label="产品能力">
          <span>对话决策</span>
          <button type="button" onClick={() => setShowWeather(true)}>
            实时天气
          </button>
          <button type="button" onClick={() => setShowWeather(true)}>
            地图钓点
          </button>
        </nav>
        <button className="lure-profile-button" onClick={() => setShowProfile(true)}>
          我的装备 <ArrowUpRight aria-hidden="true" />
        </button>
      </header>

      {/* 居中的对话卡片 */}
      <section className="lure-chat-center">
        <section className="lure-chat-card" aria-label="与老付对话">
          <h2 className="sr-only">与老付对话</h2>
          <div className="lure-chat-head">
            <div className="lure-assistant-avatar">付</div>
            <div>
              <strong>老付</strong>
              <span>
                <i /> 你的路亚搭子
              </span>
            </div>
            <button onClick={() => setShowProfile(true)} aria-label="打开我的装备">
              •••
            </button>
          </div>
          <ChatView
            messages={messages}
            loading={loading}
            onSend={send}
            onLocated={setUserLocation}
          />
          <p className="lure-privacy-note">位置仅在授权后使用 · 私密钓点不会公开</p>
        </section>
      </section>

      {/* 底部实时天气与附近钓点 */}
      <LivePanel
        location={userLocation}
        species={species}
        travelMinutes={travelMinutes}
        onSend={send}
        onLocated={setUserLocation}
      />

      {showWeather && <WeatherDashboard onClose={() => setShowWeather(false)} />}
      {showProfile && <ProfilePanel onClose={() => setShowProfile(false)} />}
    </main>
  );
}
