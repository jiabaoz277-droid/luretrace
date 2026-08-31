"use client";

import dynamic from "next/dynamic";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ChatView } from "@/components/chat/ChatView";
import { LoginView } from "@/components/LoginView";
import { ProfilePanel } from "@/components/profile/ProfilePanel";
import { RippleLayer } from "@/components/RippleLayer";
import { useChat } from "@/hooks/useChat";
import {
  useDashboardData,
  type DashboardCoordinates,
} from "@/hooks/useDashboardData";
import { apiFetch } from "@/lib/api";

const SpotsMap = dynamic(
  () => import("@/components/chat/SpotsMap").then((module) => module.SpotsMap),
  { ssr: false },
);

const speciesCards = [
  { name: "翘嘴", latin: "Culter alburnus", layer: "中上层", temp: "18–30°C", lure: "亮片 · 米诺 · 沉水铅笔", tag: "低光窗口" },
  { name: "鳜鱼", latin: "Siniperca chuatsi", layer: "底层", temp: "15–28°C", lure: "德州 · 软饵 · VIB", tag: "结构区" },
  { name: "鲈鱼", latin: "Micropterus salmoides", layer: "中下层", temp: "依水域而定", lure: "德州 · 倒吊 · Crank", tag: "障碍区" },
  { name: "马口", latin: "Opsariichthys bidens", layer: "中上层", temp: "冷水溪流", lure: "小亮片 · 飞蝇", tag: "微物" },
];

function ArrowIcon() {
  return <span aria-hidden="true">↗</span>;
}

function parseTravelMinutes(radius?: string | null) {
  if (!radius) return undefined;
  const hours = radius.match(/(\d+)\s*小时/);
  if (hours) return Number(hours[1]) * 60;
  const minutes = radius.match(/(\d+)\s*分钟/);
  return minutes ? Number(minutes[1]) : undefined;
}

function conclusionLabel(value?: "go" | "conditional" | "no_go") {
  if (value === "go") return "建议去，优先抓住高分窗口";
  if (value === "conditional") return "可以去，但有效窗口较短";
  if (value === "no_go") return "今天不建议出钓";
  return "正在结合实时数据判断";
}

export default function Home() {
  const { messages, loading: chatLoading, send } = useChat();
  const [showProfile, setShowProfile] = useState(false);
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [placeInput, setPlaceInput] = useState("杭州");
  const [activePlace, setActivePlace] = useState("杭州");
  const [coordinates, setCoordinates] = useState<DashboardCoordinates | null>(null);
  const [saved, setSaved] = useState(false);

  // 已定位后，每条消息都带上最新坐标，避免后端会话丢失定位又追问地点
  const sendWithLocation = useCallback(
    (text: string, context?: { lat?: number; lon?: number }) => {
      const next =
        context ??
        (coordinates ? { lat: coordinates.lat, lon: coordinates.lon } : undefined);
      send(text, next);
    },
    [send, coordinates],
  );

  const latestPlan = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].plan) return messages[index].plan ?? null;
    }
    return null;
  }, [messages]);

  const travelMinutes = useMemo(
    () => parseTravelMinutes(latestPlan?.travel_radius),
    [latestPlan?.travel_radius],
  );
  const { data: dashboard, loading: dashboardLoading, error: dashboardError } =
    useDashboardData({
      place: activePlace,
      coordinates,
      species: latestPlan?.target_species ?? undefined,
      travelMinutes,
    });

  useEffect(() => {
    let cancelled = false;
    void apiFetch("/api/v1/auth/session").then((response) => {
      if (!cancelled) setAuthed(response.ok);
    }).catch(() => {
      if (!cancelled) setAuthed(false);
    });
    const onUnauthorized = () => setAuthed(false);
    window.addEventListener("lure:unauthorized", onUnauthorized);
    return () => {
      cancelled = true;
      window.removeEventListener("lure:unauthorized", onUnauthorized);
    };
  }, []);

  const displayScores = useMemo(() => dashboard?.fish_scores.slice(0, 8) ?? [], [dashboard]);
  const bestScore = useMemo(
    () => displayScores.reduce((best, item) => (item.score > best.score ? item : best), displayScores[0] ?? { hour: "--", score: 0, temp: 0, condition: "" }),
    [displayScores],
  );
  const current = dashboard?.current;
  const decisionScore = latestPlan?.score ?? bestScore.score;
  const bestWindow = latestPlan?.best_window ?? (bestScore.hour !== "--" ? `${bestScore.hour}:00–${String((Number(bestScore.hour) + 2) % 24).padStart(2, "0")}:00` : "待定位");
  const targetSpecies = latestPlan?.target_species ?? "翘嘴 · 鳜鱼";
  const planDetail = latestPlan?.plan_detail;
  const weatherSource = dashboard?.mock ? "模拟降级" : dashboard ? "实时数据" : "等待数据";
  const factors = [
    { label: `气压${current?.pressure_trend ?? "待获取"}`, delta: current?.pressure_trend === "缓升" ? 12 : current?.pressure_trend === "下降" ? -10 : 0 },
    { label: current && current.precip_prob <= 20 ? "降水概率低" : "注意降水", delta: current ? (current.precip_prob <= 20 ? 10 : current.precip_prob >= 60 ? -15 : 0) : 0 },
    { label: current ? `${current.wind_dir}${current.wind_scale}级` : "风况待获取", delta: current ? (current.wind_scale <= 3 ? 8 : current.wind_scale >= 6 ? -20 : 0) : 0 },
  ];

  function submitPlace(event: FormEvent) {
    event.preventDefault();
    const nextPlace = placeInput.trim();
    if (!nextPlace) return;
    setCoordinates(null);
    setActivePlace(nextPlace);
  }

  function handleLocated(name: string, nextCoordinates?: DashboardCoordinates) {
    setPlaceInput(name);
    setActivePlace(name);
    setCoordinates(nextCoordinates ?? null);
  }

  if (authed === null) return null;
  if (!authed) return <LoginView onLogin={() => setAuthed(true)} />;

  return (
    <main className="product-shell">
      <div className="app-sheen" aria-hidden="true" />
      <RippleLayer />
      <header className="product-topbar">
        <a className="product-brand" href="#top" aria-label="路迹首页">
          <span className="product-brand-mark">L</span>
          <span><strong>路迹</strong><small>LURETRACE</small></span>
        </a>
        <nav aria-label="主导航">
          <a href="#assistant">问路迹</a>
          <a href="#windows">今日窗口</a>
          <a href="#spots">附近水域</a>
        </nav>
        <button className="product-profile" type="button" onClick={() => setShowProfile(true)}>
          <span className="profile-dot">◎</span> 我的装备
        </button>
      </header>

      <div className="product-main">
        <section className="context-banner" id="top">
          <img className="context-fish" src="/login-fish.png" alt="" aria-hidden="true" />
          <div className="context-copy">
            <div className="live-status"><i></i>{weatherSource} · {dashboard?.location ?? activePlace}</div>
            <h1>{dashboard?.location ?? activePlace}，<br />今天怎么钓？</h1>
            <p>{conclusionLabel(latestPlan?.conclusion)}。路迹已把天气、时间和附近水域整理成可执行方案。</p>
            <button type="button" onClick={() => { document.querySelector<HTMLInputElement>("#chat-input")?.focus(); location.hash = "assistant"; }}>
              直接问路迹 <ArrowIcon />
            </button>
          </div>
          <div className="context-metrics" aria-label="今日实时参考">
            <div className="metric-score"><small>今日参考</small><strong>{decisionScore || "—"}</strong><span>/100</span></div>
            <div><small>首选窗口</small><strong>{bestWindow}</strong></div>
            <div><small>当前天气</small><strong>{current ? `${current.condition} · ${current.temp}°` : "正在读取"}</strong></div>
            <div><small>风况 / 气压</small><strong>{current ? `${current.wind_dir}${current.wind_scale}级 · ${current.pressure}hPa` : "正在读取"}</strong></div>
          </div>
        </section>

        <section className="workspace-grid">
          <article className="chat-workspace" id="assistant">
            <div className="workspace-head">
              <div><span className="workspace-avatar">L</span><div><strong>问路迹</strong><small><i></i> AI 路亚决策助手在线</small></div></div>
              <button type="button" onClick={() => setShowProfile(true)}>装备档案</button>
            </div>
            <ChatView messages={messages} loading={chatLoading} onSend={sendWithLocation} onLocated={handleLocated} />
            <div className="workspace-note">⌖ 位置只在授权后使用 · 私密钓点不会公开</div>
          </article>

          <aside className="decision-rail">
            <section className="decision-card">
              <div className="rail-heading"><div><small>实时决策</small><h2>今日判断</h2></div><span className="rail-live">实时</span></div>
              <div className="decision-summary"><strong>{decisionScore || "—"}</strong><div><span>综合参考</span><b>{conclusionLabel(latestPlan?.conclusion)}</b></div></div>
              <div className="decision-factors">
                {factors.map((factor) => <div key={factor.label}><span>{factor.label}</span><b className={factor.delta < 0 ? "negative" : ""}>{factor.delta > 0 ? "+" : ""}{factor.delta}</b></div>)}
              </div>
              <div className="target-row"><span>优先对象鱼</span><strong>{targetSpecies}</strong></div>
            </section>

            <section className="nearby-rail">
              <div className="rail-heading"><div><small>附近推荐</small><h2>附近水域</h2></div><a href="#spots">查看地图 →</a></div>
              <div className="nearby-rows">
                {dashboard?.spots.slice(0, 3).map((spot, index) => (
                  <button key={`${spot.name}-${spot.lat}-${spot.lon}`} type="button" onClick={() => send(`帮我规划${spot.name}，目标鱼是${latestPlan?.target_species ?? "翘嘴"}`)}>
                    <span>0{index + 1}</span><div><strong>{spot.name}</strong><small>{spot.spot_type} · {spot.distance_km}km</small></div><i>↗</i>
                  </button>
                )) ?? <p className="rail-empty">{dashboardLoading ? "正在读取附近水域…" : "定位后显示附近水域"}</p>}
              </div>
            </section>
          </aside>
        </section>

        {latestPlan && <section className="plan-workspace" aria-label="生成的出钓方案">
          <div className="plan-workspace-head"><div><small>方案 V{latestPlan.version}</small><h2>{latestPlan.location ?? dashboard?.location ?? activePlace} · {latestPlan.target_species ?? "路亚"}执行计划</h2></div><button type="button" onClick={() => setSaved(!saved)}>{saved ? "✓ 已保存" : "+ 保存计划"}</button></div>
          <div className="plan-rows">
            <article><span>01</span><div><small>时间</small><strong>{latestPlan.best_window ?? latestPlan.time_window ?? "待确认"}</strong><p>{latestPlan.backup_window ? `备选 ${latestPlan.backup_window}` : "到位后先观察水面活动与风向"}</p></div></article>
            <article><span>02</span><div><small>标点</small><strong>{planDetail?.spot_type ?? "入水口 · 深浅交界"}</strong><p>优先搜索{planDetail?.water_layer ?? "目标鱼活跃水层"}</p></div></article>
            <article><span>03</span><div><small>打法</small><strong>{planDetail?.weight_color ?? "适配克重"} {planDetail?.primary_lure ?? "常用拟饵"}</strong><p>{planDetail?.action ?? "先搜索再精细作钓"}</p></div></article>
            <article className="plan-warning"><span>!</span><div><small>注意</small><strong>{latestPlan.safety[0] ?? "开放性现场核实"}</strong><p>{latestPlan.risks[0] ?? "以现场告示为准"}</p></div></article>
          </div>
        </section>}

        <section className="insight-grid">
          <article className="window-product-card" id="windows">
            <div className="product-card-head"><div><small>鱼口趋势 · {dashboard?.mock ? "降级数据" : "实时"}</small><h2>逐小时鱼口窗口</h2><p>{dashboardLoading ? "正在读取实时天气…" : dashboardError ?? `日出 ${dashboard?.sunrise ?? "—"} · 日落 ${dashboard?.sunset ?? "—"}`}</p></div><span className="best-pill">最高 {bestScore.score || "—"}</span></div>
            <div className="product-chart">
              {displayScores.map((window) => <button type="button" key={window.hour} onClick={() => send(`今天${window.hour}点到${(Number(window.hour) + 2) % 24}点去${dashboard?.location ?? activePlace}钓行不行`)} title="点击继续问路迹"><small>{window.score}</small><i className={window.score >= 70 ? "hot" : ""} style={{ height: `${Math.max(window.score, 8)}%` }}></i><strong>{window.hour}:00</strong><span>{window.temp}°</span></button>)}
            </div>
            <div className="product-chart-note"><i></i><strong>{bestWindow}</strong><span>点击任一时段，让路迹继续细化方案</span></div>
          </article>

          <article className="map-product-card" id="spots">
            <div className="product-card-head map-head"><div><small>钓点地图 · 实时</small><h2>附近水域</h2></div><form onSubmit={submitPlace}><input value={placeInput} onChange={(event) => setPlaceInput(event.target.value)} aria-label="城市或水域" placeholder="杭州 / 富春江" /><button type="submit">{dashboardLoading ? "…" : "搜索"}</button></form></div>
            <div className="product-map">
              {dashboard?.spots.length ? <SpotsMap spots={dashboard.spots} /> : <div className="map-empty">{dashboardLoading ? "正在加载地图…" : dashboardError ?? "换一个地点试试"}</div>}
            </div>
            <p className="map-disclaimer">点位仅作决策参考，开放性、收费和禁钓规定以现场告示为准。</p>
          </article>
        </section>

        <section className="species-product" id="species">
          <div className="species-product-head"><div><small>对象鱼策略</small><h2>常用对象鱼策略</h2></div><a href="#assistant">问具体鱼种 <ArrowIcon /></a></div>
          <div className="species-product-grid">
            {speciesCards.map((fish, index) => <article key={fish.name}><span>0{index + 1}</span><div className="fish-title"><small>{fish.latin}</small><h3>{fish.name}</h3></div><dl><div><dt>水层</dt><dd>{fish.layer}</dd></div><div><dt>常用拟饵</dt><dd>{fish.lure}</dd></div></dl><b>{fish.tag}</b></article>)}
          </div>
        </section>

        <footer className="product-footer"><span>路迹 LURETRACE</span><p>实时数据辅助判断 · 出钓安全以现场情况为准</p><small>© 2026</small></footer>
      </div>

      <nav className="mobile-nav product-mobile-nav" aria-label="移动端导航"><a href="#top"><span>⌂</span>首页</a><a href="#windows"><span>⌁</span>窗口</a><a className="ask-button" href="#assistant"><span>+</span>问路迹</a><a href="#spots"><span>⌖</span>水域</a><button type="button" onClick={() => setShowProfile(true)}><span>◎</span>我的</button></nav>
      {showProfile && <ProfilePanel onClose={() => setShowProfile(false)} />}
    </main>
  );
}
