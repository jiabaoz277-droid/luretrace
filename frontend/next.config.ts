import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8003";

const securityHeaders = [
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(self)" },
  {
    key: "Content-Security-Policy",
    value: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://tile.openstreetmap.org; font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
  },
];

const nextConfig: NextConfig = {
  // 部署到 veFaaS 时使用 standalone 输出（node server.js 启动）
  output: "standalone",
  // 允许局域网设备访问 dev 资源（手机/其他设备通过局域网 IP 打开时不会被拦截）
  allowedDevOrigins: ["127.0.0.1", "192.168.110.181"],
  // standalone 自托管下图片优化路由不可用（返回 400），关闭优化让图片直连加载
  images: { unoptimized: true },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async rewrites() {
    return [
      {
        // 前端同源代理到后端，避免 CORS；BACKEND_URL 在部署 build 时注入
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
