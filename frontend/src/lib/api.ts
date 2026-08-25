/** API 基础地址：优先环境变量，否则按当前页面 hostname 自动推导后端端口。 */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8003`
    : "http://localhost:8003");
