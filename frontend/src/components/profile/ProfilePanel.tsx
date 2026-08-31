"use client";

import { Check } from "lucide-react";
import { useState } from "react";
import { useProfile } from "@/hooks/useProfile";
import type { ProfileData } from "@/types/api";

export function ProfilePanel({ onClose }: { onClose: () => void }) {
  const { profile, loaded, save } = useProfile();

  return (
    <div className="modal-backdrop">
      <button className="modal-dismiss" type="button" aria-label="关闭装备面板" onClick={onClose}></button>
      {loaded ? <ProfileForm initial={profile} onSave={save} onClose={onClose} /> : <section className="gear-modal" role="dialog" aria-modal="true"><p>正在加载装备档案…</p></section>}
    </div>
  );
}

function ProfileForm({
  initial,
  onSave,
  onClose,
}: {
  initial: ProfileData;
  onSave: (profile: ProfileData) => Promise<void>;
  onClose: () => void;
}) {
  const [rods, setRods] = useState((initial.rods || []).join("、"));
  const [reels, setReels] = useState((initial.reels || []).join("、"));
  const [lines, setLines] = useState((initial.lines || []).join("、"));
  const [lures, setLures] = useState((initial.lures || []).join("、"));
  const [avoidMethods, setAvoidMethods] = useState((initial.avoid_methods || []).join("、"));
  const [radius, setRadius] = useState(initial.max_travel_radius || "");
  const [noNight, setNoNight] = useState((initial.constraints || []).includes("不夜钓"));
  const [noWading, setNoWading] = useState((initial.constraints || []).includes("不涉水"));
  const [saved, setSaved] = useState(false);

  const split = (value: string) => value.split(/[,，、]/).map((item) => item.trim()).filter(Boolean);

  async function handleSave() {
    const constraints: string[] = [];
    if (noNight) constraints.push("不夜钓");
    if (noWading) constraints.push("不涉水");
    await onSave({
      ...initial,
      rods: split(rods),
      reels: split(reels),
      lines: split(lines),
      lures: split(lures),
      avoid_methods: split(avoidMethods),
      max_travel_radius: radius || null,
      constraints,
    });
    setSaved(true);
    window.setTimeout(onClose, 700);
  }

  return (
    <section className="gear-modal" role="dialog" aria-modal="true" aria-labelledby="gear-title">
      <button className="modal-close" type="button" onClick={onClose} aria-label="关闭">×</button>
      <small>MY TACKLE</small>
      <h2 id="gear-title">让建议适配你手里的装备</h2>
      <p>路迹会优先使用已有装备，不会默认引导购买。</p>
      <div className="profile-fields">
        <label className="profile-field"><span>竿（型号/调性）</span><input value={rods} onChange={(event) => setRods(event.target.value)} placeholder="如：ML调路亚竿" /></label>
        <label className="profile-field"><span>轮（型号/类型）</span><input value={reels} onChange={(event) => setReels(event.target.value)} placeholder="如：纺车轮2500" /></label>
        <label className="profile-field"><span>线（线号/材质）</span><input value={lines} onChange={(event) => setLines(event.target.value)} placeholder="如：0.8号PE" /></label>
        <label className="profile-field"><span>常用拟饵</span><input value={lures} onChange={(event) => setLures(event.target.value)} placeholder="如：7g亮片、米诺" /></label>
        <label className="profile-field"><span>不愿使用的钓法</span><input value={avoidMethods} onChange={(event) => setAvoidMethods(event.target.value)} placeholder="可留空" /></label>
        <label className="profile-field"><span>最大车程</span><input value={radius} onChange={(event) => setRadius(event.target.value)} placeholder="如：40分钟" /></label>
      </div>
      <div className="profile-checks">
        <label><input type="checkbox" checked={noNight} onChange={(event) => setNoNight(event.target.checked)} />不夜钓</label>
        <label><input type="checkbox" checked={noWading} onChange={(event) => setNoWading(event.target.checked)} />不涉水</label>
      </div>
      <div className="profile-actions">
        <button className="save-gear" type="button" onClick={handleSave}>{saved && <Check aria-hidden="true" size={15} />} {saved ? "已保存" : "保存装备"}</button>
        <button className="secondary" type="button" onClick={onClose}>关闭</button>
      </div>
    </section>
  );
}
