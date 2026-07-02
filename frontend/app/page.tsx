"use client";

import { useEffect, useState } from "react";
import VoiceOrb, { OrbState } from "@/components/VoiceOrb";
import MicButton from "@/components/MicButton";
import ChatPanel, { ChatMessage } from "@/components/ChatPanel";
import { checkHealth, sendChatMessage, type HealthResponse } from "@/lib/api";

export default function Home() {
  const [orbState, setOrbState] = useState<OrbState>("idle");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sendingText, setSendingText] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const result = await checkHealth();
        if (!cancelled) setHealth(result);
      } catch {
        if (!cancelled) setHealth(null);
      }
    }
    poll();
    const interval = setInterval(poll, 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  async function handleSendText(text: string) {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setSendingText(true);
    setOrbState("thinking");
    try {
      const response = await sendChatMessage(text, conversationId);
      setConversationId(response.conversation_id);
      setMessages((prev) => [...prev, { role: "assistant", content: response.reply }]);
      setOrbState("idle");
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I ran into an error processing that." },
      ]);
      setOrbState("error");
      setTimeout(() => setOrbState("idle"), 2000);
    } finally {
      setSendingText(false);
    }
  }

  const backendDown = health === null;
  const degraded = health && (!health.ollama_reachable || !health.piper_available);

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 p-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Jarvis</h1>
          <p className="text-sm text-jarvis-muted">Phase 1 — voice conversation system</p>
        </div>
        <StatusBadge backendDown={!!backendDown} degraded={!!degraded} health={health} />
      </header>

      <section className="flex flex-col items-center justify-center gap-4 rounded-xl border border-white/10 bg-jarvis-panel py-10">
        <VoiceOrb state={orbState} />
        <MicButton
          conversationId={conversationId}
          onConversationId={setConversationId}
          onUserText={(text) => setMessages((prev) => [...prev, { role: "user", content: text }])}
          onAssistantText={(text) =>
            setMessages((prev) => [...prev, { role: "assistant", content: text }])
          }
          onStateChange={setOrbState}
          disabled={backendDown}
        />
      </section>

      <section className="min-h-[360px] flex-1">
        <ChatPanel messages={messages} onSendText={handleSendText} disabled={sendingText || backendDown} />
      </section>
    </main>
  );
}

function StatusBadge({
  backendDown,
  degraded,
  health,
}: {
  backendDown: boolean;
  degraded: boolean;
  health: HealthResponse | null;
}) {
  if (backendDown) {
    return (
      <span className="rounded-full bg-red-500/15 px-3 py-1 text-xs font-medium text-red-400">
        Backend offline
      </span>
    );
  }
  if (degraded) {
    const missing = [
      !health?.ollama_reachable && "Ollama",
      !health?.piper_available && "Piper voice",
    ].filter(Boolean);
    return (
      <span className="rounded-full bg-amber-500/15 px-3 py-1 text-xs font-medium text-amber-400">
        Degraded: {missing.join(", ")} unavailable
      </span>
    );
  }
  return (
    <span className="rounded-full bg-jarvis-accent/15 px-3 py-1 text-xs font-medium text-jarvis-accent">
      All systems online
    </span>
  );
}
