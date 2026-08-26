"use client";

import { useEffect, useState } from "react";
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
            <strong>路亚问问</strong>
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
      <LivePanel location={userLocation} onSend={send} />

      {showWeather && <WeatherDashboard onClose={() => setShowWeather(false)} />}
      {showProfile && <ProfilePanel onClose={() => setShowProfile(false)} />}
    </main>
  );
}
