"use client";

import { useRef, useState } from "react";
import { synthesizeSpeech, transcribeAudio, sendChatMessage } from "@/lib/api";
import type { OrbState } from "./VoiceOrb";

interface MicButtonProps {
  conversationId: string | undefined;
  onConversationId: (id: string) => void;
  onUserText: (text: string) => void;
  onAssistantText: (text: string) => void;
  onStateChange: (state: OrbState) => void;
  disabled?: boolean;
}

/**
 * Push-to-talk mic button driving the full voice loop:
 * record -> transcribe (Whisper) -> chat (Ollama + memory) -> synthesize (Piper) -> play.
 *
 * Uses sequential REST calls rather than the WebSocket endpoint for
 * simplicity and easier debugging in Phase 1. The backend's /api/voice/ws
 * endpoint already supports a lower-latency streaming version of this same
 * flow; swapping this component to use it is a Phase 2 optimization that
 * doesn't require backend changes.
 */
export default function MicButton({
  conversationId,
  onConversationId,
  onUserText,
  onAssistantText,
  onStateChange,
  disabled,
}: MicButtonProps) {
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });
        void runVoiceTurn(audioBlob);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
      onStateChange("listening");
    } catch (err) {
      console.error("Microphone access failed:", err);
      onStateChange("error");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }

  async function runVoiceTurn(audioBlob: Blob) {
    try {
      onStateChange("thinking");

      const { text: userText } = await transcribeAudio(audioBlob);
      onUserText(userText);

      const chatResponse = await sendChatMessage(userText, conversationId);
      onConversationId(chatResponse.conversation_id);
      onAssistantText(chatResponse.reply);

      onStateChange("speaking");
      const speechBlob = await synthesizeSpeech(chatResponse.reply);
      const audioUrl = URL.createObjectURL(speechBlob);
      const audio = new Audio(audioUrl);
      audio.onended = () => onStateChange("idle");
      audio.onerror = () => onStateChange("idle");
      await audio.play();
    } catch (err) {
      console.error("Voice turn failed:", err);
      onStateChange("error");
      setTimeout(() => onStateChange("idle"), 2000);
    }
  }

  return (
    <button
      onClick={recording ? stopRecording : startRecording}
      disabled={disabled}
      className={`btn-mic ${recording ? "btn-mic--recording" : ""}`}
      aria-pressed={recording}
    >
      {recording ? (
        <>
          <span className="btn-mic-dot" aria-hidden="true" />
          Stop &amp; send
        </>
      ) : (
        <>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="btn-mic-icon"
            aria-hidden="true"
          >
            <path
              d="M12 15.5C13.66 15.5 15 14.16 15 12.5V6.5C15 4.84 13.66 3.5 12 3.5C10.34 3.5 9 4.84 9 6.5V12.5C9 14.16 10.34 15.5 12 15.5Z"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M5 11V12.5C5 16.09 7.91 19 11.5 19H12.5C16.09 19 19 16.09 19 12.5V11"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M12 19V21.5"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Hold to talk
        </>
      )}
    </button>
  );
}