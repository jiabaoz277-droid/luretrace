import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  // 网关会追加该头；只在明确为 HTTP 时跳转，避免本地开发和代理循环。
  if (process.env.NODE_ENV === "production" && request.headers.get("x-forwarded-proto") === "http") {
    const forwardedHost = request.headers.get("x-forwarded-host")?.split(",")[0].trim();
    const host = forwardedHost ?? request.headers.get("host")?.trim();
    // 仅信任平台网关域名，防止伪造 Host 形成开放重定向。
    if (host && /^[a-z0-9-]+\.apigateway-cn-beijing\.volceapi\.com$/i.test(host)) {
      const url = new URL(`${request.nextUrl.pathname}${request.nextUrl.search}`, `https://${host}`);
      return NextResponse.redirect(url, 308);
    }
  }
  return NextResponse.next();
}
