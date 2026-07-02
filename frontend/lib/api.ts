/**
 * Typed API client for the Jarvis backend.
 *
 * Centralizing fetch calls here means components never construct URLs or
 * parse response shapes themselves — if the backend contract changes, only
 * this file needs updating.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export interface ChatResponse {
  conversation_id: string;
  reply: string;
  model: string;
}

export interface HealthResponse {
  status: string;
  ollama_reachable: boolean;
  whisper_loaded: boolean;
  piper_available: boolean;
}

export class JarvisApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function handle<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ message: response.statusText }));
    throw new JarvisApiError(response.status, body.message || "Request failed");
  }
  return response.json();
}

export async function sendChatMessage(
  message: string,
  conversationId?: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  return handle<ChatResponse>(response);
}

export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/api/health`);
  return handle<HealthResponse>(response);
}

export async function transcribeAudio(blob: Blob): Promise<{ text: string }> {
  const formData = new FormData();
  formData.append("file", blob, "recording.webm");
  const response = await fetch(`${API_BASE}/api/voice/transcribe`, {
    method: "POST",
    body: formData,
  });
  return handle<{ text: string }>(response);
}

export async function synthesizeSpeech(text: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/voice/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ message: response.statusText }));
    throw new JarvisApiError(response.status, body.message || "Speech synthesis failed");
  }
  return response.blob();
}

/** Opens the full-duplex voice conversation WebSocket. */
export function openVoiceSocket(): WebSocket {
  return new WebSocket(`${WS_BASE}/api/voice/ws`);
}
