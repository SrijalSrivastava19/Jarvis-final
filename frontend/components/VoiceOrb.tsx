"use client";

export type OrbState = "idle" | "listening" | "thinking" | "speaking" | "error";

const STATE_LABELS: Record<OrbState, string> = {
  idle: 'Say "Hey Jarvis" or tap the mic',
  listening: "Listening...",
  thinking: "Thinking...",
  speaking: "Speaking...",
  error: "Something went wrong",
};

export default function VoiceOrb({ state }: { state: OrbState }) {
  return (
    <div className="orb-container">
      <div className={`orb-stage orb--${state}`}>
        <div className="orb-ambient-glow" />
        <div className="orb-ring orb-ring--outer" />
        <div className="orb-ring orb-ring--inner" />

        <div className="orb-core">
          <div className="orb-pulse-ring" />
          <div className="orb-equalizer" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>

      <p className="orb-label" role="status" aria-live="polite">
        {STATE_LABELS[state]}
      </p>
    </div>
  );
}