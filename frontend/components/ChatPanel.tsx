"use client";

import { useEffect, useRef, useState } from "react";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatPanelProps {
  messages: ChatMessage[];
  onSendText: (text: string) => void;
  disabled?: boolean;
}

export default function ChatPanel({ messages, onSendText, disabled }: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || disabled) return;
    onSendText(trimmed);
    setDraft("");
  }

  return (
    <div className="glass-panel chat-card">
      <div className="chat-card-header">
        <span className="chat-card-title">Conversation</span>
        <span className="chat-card-status">
          <span className="chat-card-status-dot" />
          {disabled ? "Busy" : "Online"}
        </span>
      </div>

      <div ref={scrollRef} className="chat-scroll">
        {messages.length === 0 && (
          <p className="chat-empty">
            No messages yet. Type below or use the mic to start talking to Jarvis.
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`chat-bubble ${
              msg.role === "user" ? "chat-bubble--user" : "chat-bubble--assistant"
            }`}
          >
            {msg.content}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="composer">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={disabled}
          placeholder="Message Jarvis..."
          className="composer-input"
          aria-label="Message Jarvis"
        />
        <button
          type="submit"
          disabled={disabled || !draft.trim()}
          className="btn-send"
          aria-label="Send message"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
          >
            <path
              d="M4 12L20 4L13 20L11 13L4 12Z"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinejoin="round"
              strokeLinecap="round"
              fill="currentColor"
            />
          </svg>
        </button>
      </form>
    </div>
  );
}