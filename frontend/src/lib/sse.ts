/** SSE 事件解析：chunk* → done | error（契约见前端开发技术手册第四节）。 */
import type { InsightStats, Plan, Report, Spot, Step } from "@/types/api";

export type DonePayload = {
  type:
    | "plan"
    | "clarify"
    | "onsite"
    | "report"
    | "insight"
    | "reply"
    | "compliance_refusal"
    | "out_of_scope";
  reply: string;
  plan?: Plan;
  missing?: string[];
  steps?: Step[];
  report?: Report;
  quick_options?: string[];
  insight?: InsightStats;
  spots?: Spot[];
};

export type SSEEvent =
  | { type: "chunk"; content: string; session_id?: string }
  | { type: "done"; session_id?: string; payload: DonePayload }
  | { type: "error"; error: { code: string; message: string } };

/** 解析单个 `data: {...}` 行，非法/未知类型返回 null（纯函数，可离线单测）。 */
export function parseSSEEvent(line: string): SSEEvent | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith("data: ")) return null;
  try {
    const data = JSON.parse(trimmed.slice(6)) as Record<string, unknown>;
    if (data.type === "chunk") {
      return { type: "chunk", content: String(data.content ?? ""), session_id: data.session_id as string | undefined };
    }
    if (data.type === "done") {
      return { type: "done", session_id: data.session_id as string | undefined, payload: data.payload as DonePayload };
    }
    if (data.type === "error") {
      return { type: "error", error: data.error as { code: string; message: string } };
    }
  } catch {
    // 忽略无法解析的行
  }
  return null;
}
