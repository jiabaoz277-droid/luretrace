import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Plan } from "@/types/api";
import { PlanCard } from "./PlanCard";

const plan: Plan = {
  version: 1,
  conclusion: "go",
  confidence: "high",
  score: 90,
  best_window: "05:00–07:00",
  location: "杭州",
  target_species: "翘嘴",
  plan_detail: {
    spot_type: "入水口",
    water_layer: "中上层",
    primary_lure: "亮片",
    weight_color: "7–10g/银色",
    action: "扇形搜索",
  },
  factors: ["低光窗口"],
  risks: [],
  safety: [],
  data_basis: {},
};

describe("PlanCard", () => {
  it("渲染结论、窗口与目标鱼", () => {
    render(<PlanCard plan={plan} />);
    expect(screen.getByText(/建议去/)).toBeInTheDocument();
    expect(screen.getByText(/05:00–07:00/)).toBeInTheDocument();
    expect(screen.getByText("翘嘴")).toBeInTheDocument();
    expect(screen.getByText(/亮片/)).toBeInTheDocument();
  });

  it("安全提示优先展示", () => {
    render(<PlanCard plan={{ ...plan, conclusion: "no_go", safety: ["雷暴，停止出钓"] }} />);
    expect(screen.getByText(/雷暴，停止出钓/)).toBeInTheDocument();
  });
});
