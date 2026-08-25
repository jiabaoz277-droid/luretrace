/** 统一前端错误结构（手册 12.3）：用户看到 userMessage，调试保留 code。 */
export type AppError = {
  code: string;
  message: string;
  userMessage: string;
  retryable: boolean;
};

export const NETWORK_ERROR: AppError = {
  code: "network_error",
  message: "network error",
  userMessage: "无法连接服务，请确认后端已启动（端口 8003）",
  retryable: true,
};

export function toAppError(raw: { code?: string; message?: string } | undefined): AppError {
  const code = raw?.code || "internal_error";
  return {
    code,
    message: raw?.message || code,
    userMessage: raw?.message || "出错了，请稍后重试",
    retryable: code === "network_error" || code === "rate_limited",
  };
}
