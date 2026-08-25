/** 前后端契约类型：与 /api/v1 返回结构一一对应。 */

export type PlanDetail = {
  spot_type?: string | null;
  water_layer?: string | null;
  primary_lure?: string | null;
  backup_lure?: string | null;
  weight_color?: string | null;
  action?: string | null;
  adjust_condition?: string | null;
};

export type Plan = {
  version: number;
  location?: string | null;
  time_window?: string | null;
  target_species?: string | null;
  travel_radius?: string | null;
  conclusion: "go" | "conditional" | "no_go";
  confidence: "high" | "mid" | "low";
  score: number;
  best_window?: string | null;
  backup_window?: string | null;
  factors: string[];
  plan_detail: PlanDetail;
  risks: string[];
  safety: string[];
  data_basis: Record<string, unknown>;
  history_note?: string | null;
};

export type Step = { action: string; duration: string; upgrade: string };

export type Report = {
  id: number;
  result_type: string;
  result_label: string;
  species?: string | null;
  count?: number | null;
  lure?: string | null;
  review?: string | null;
  review_confirmed: boolean;
};

export type InsightStats = {
  total: number;
  result_dist: Record<string, number>;
  top_species: { species: string; count: number }[];
  recent: Report[];
};

export type ProfileData = {
  rods: string[];
  reels: string[];
  lines: string[];
  lures: string[];
  avoid_methods: string[];
  max_travel_radius?: string | null;
  night_fishing: boolean;
  wading: boolean;
  home_location?: string | null;
  constraints: string[];
};

export type Msg = {
  role: "user" | "assistant";
  content: string;
  plan?: Plan | null;
  missing?: string[];
  steps?: Step[];
  report?: Report | null;
  quick_options?: string[];
  insight?: InsightStats | null;
  error?: string;
};
