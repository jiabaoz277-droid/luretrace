import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "路亚问问",
  description: "对话式路亚出钓决策助手",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
