"use client";

import { useState } from "react";
import { ChatView } from "@/components/chat/ChatView";
import { ProfilePanel } from "@/components/profile/ProfilePanel";
import { useChat } from "@/hooks/useChat";

export default function Home() {
  const { messages, loading, send } = useChat();
  const [showProfile, setShowProfile] = useState(false);

  return (
    <div className="mx-auto flex h-dvh max-w-md flex-col bg-paper">
      <header className="flex items-center justify-between bg-ink px-4 py-3">
        <div className="flex items-center gap-2.5">
          <span className="inline-block h-6 w-1.5 rounded bg-daiwa" />
          <div>
            <h1 className="text-lg font-bold leading-tight text-white">路亚问问</h1>
            <p className="text-xs text-white/55">对话式出钓决策助手</p>
          </div>
        </div>
        <button
          onClick={() => setShowProfile(true)}
          className="rounded-full border border-white/25 px-3.5 py-1.5 text-sm text-white"
        >
          我的
        </button>
      </header>

      <ChatView messages={messages} loading={loading} onSend={send} />

      {showProfile && <ProfilePanel onClose={() => setShowProfile(false)} />}
    </div>
  );
}
