/** API 基础地址：优先环境变量；默认同源（经 Next rewrites 代理到后端，避免 CORS）。 */
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

const TOKEN_KEY = "lure_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(TOKEN_KEY, token);
  }
}

export function clearToken(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

/**
 * 统一请求封装：自动附带 Bearer token；401 时清除 token 并广播未登录事件。
 */
export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${input}`, { ...init, headers });

  if (res.status === 401 && !input.startsWith("/api/v1/auth")) {
    clearToken();
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("lure:unauthorized"));
    }
  }
  return res;
}
