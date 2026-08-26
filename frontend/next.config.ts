import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8003";

const nextConfig: NextConfig = {
  // 部署到 veFaaS 时使用 standalone 输出（node server.js 启动）
  output: "standalone",
  // 允许局域网设备访问 dev 资源（手机/其他设备通过局域网 IP 打开时不会被拦截）
  allowedDevOrigins: ["192.168.110.181"],
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
