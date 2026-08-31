import type { Metadata, Viewport } from "next";
import "leaflet/dist/leaflet.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "路迹｜会给方案的路亚决策助手",
  description: "用对话完成实时出钓判断、鱼口窗口、附近水域、对象鱼与临场排障。",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0e1a24",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
