export type RuneState = {
  identity: { name: string; role: string };
  current_goal: string | null;
  active_context: Record<string, unknown>;
  working_memory: Record<string, unknown>;
  last_decision: Record<string, unknown> | null;
  last_action: Record<string, unknown> | null;
};

const API_BASE = import.meta.env.VITE_RUNE_API_URL ?? "http://127.0.0.1:8765";

export async function getState(): Promise<RuneState> {
  const response = await fetch(API_BASE + "/api/state");
  if (!response.ok) throw new Error("RUNE API unavailable");
  return response.json();
}

export async function sendMessage(message: string): Promise<string> {
  const response = await fetch(API_BASE + "/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error ?? "RUNE request failed");
  return payload.response;
}
