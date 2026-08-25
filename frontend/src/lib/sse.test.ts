import { describe, expect, it } from "vitest";
import { parseSSEEvent } from "./sse";

describe("parseSSEEvent", () => {
  it("解析 chunk 事件", () => {
    const ev = parseSSEEvent('data: {"type":"chunk","content":"你好","session_id":"abc"}');
    expect(ev).toEqual({ type: "chunk", content: "你好", session_id: "abc" });
  });

  it("解析 done 事件并透传 payload", () => {
    const ev = parseSSEEvent(
      'data: {"type":"done","session_id":"abc","payload":{"type":"plan","reply":"建议去"}}'
    );
    expect(ev).toMatchObject({
      type: "done",
      session_id: "abc",
      payload: { type: "plan", reply: "建议去" },
    });
  });

  it("解析 error 事件保留统一错误结构", () => {
    const ev = parseSSEEvent(
      'data: {"type":"error","error":{"code":"internal_error","message":"稍后重试"}}'
    );
    expect(ev).toMatchObject({
      type: "error",
      error: { code: "internal_error", message: "稍后重试" },
    });
  });

  it("忽略非法或未知类型行，不抛异常", () => {
    expect(parseSSEEvent("")).toBeNull();
    expect(parseSSEEvent("data: {broken")).toBeNull();
    expect(parseSSEEvent('data: {"type":"unknown"}')).toBeNull();
    expect(parseSSEEvent(": ping")).toBeNull();
  });
});
