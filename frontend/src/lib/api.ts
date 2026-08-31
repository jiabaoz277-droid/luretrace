/** API 基础地址：优先环境变量；默认同源（经 Next rewrites 代理到后端，避免 CORS）。 */
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

export function clearToken(): void {
  if (typeof window !== "undefined") {
    // 清理由旧版本遗留、可被脚本读取的 token。
    window.localStorage.removeItem("lure_token");
  }
}

/**
 * 统一请求封装：使用同源 HttpOnly Cookie；401 时广播未登录事件。
 */
export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});
  clearToken();
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${input}`, { ...init, headers, credentials: "same-origin" });

  if (res.status === 401 && !input.startsWith("/api/v1/auth")) {
    clearToken();
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("lure:unauthorized"));
    }
  }
  return res;
}
