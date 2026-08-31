import type { Step } from "@/types/api";

export function StepsCard({ steps }: { steps: Step[] }) {
  return (
    <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-ink">
      <p className="mb-2 font-semibold text-lime">按顺序执行，一次只改一个变量</p>
      {steps.map((s, i) => (
        <div key={i} className="mb-2 border-l-2 border-lime/30 pl-3 last:mb-0">
          <p className="font-medium">
            {i + 1}. {s.action}
          </p>
          <p className="text-ink-soft">
            观察 {s.duration}
            {s.upgrade !== "—" ? `；${s.upgrade}` : ""}
          </p>
        </div>
      ))}
    </div>
  );
}
