export type WindowInfo = {
  hwnd: number;
  pid: number;
  title: string;
  foreground?: boolean;
};

export type RuneState = {
  identity: {
    name: string;
    role: string;
    owner?: {
      subject: string;
      display_name: string;
      device_id: string;
      platform: string;
      assurance: string;
    };
  };
  current_goal: string | null;
  active_context: Record<string, unknown>;
  working_memory: Record<string, unknown>;
  last_decision: Record<string, unknown> | null;
  last_action: Record<string, unknown> | null;
  tools?: ToolSpec[];
  voice?: VoiceStatus;
  node?: {
    id?: string;
    platform?: string;
    hostname?: string;
    capabilities?: string[];
    observation?: {
      process_count?: number;
      window_count?: number;
      windows?: WindowInfo[];
      system?: {
        memory_load_percent?: number;
        memory_total_mb?: number;
        memory_available_mb?: number;
      };
      status?: string;
    };
  };
  shell?: {
    mode?: string;
    island_message?: string | null;
    workspaces?: { id: string; name: string; active: boolean }[];
  };
};

export type ToolSpec = {
  name: string;
  description: string;
  risk: string;
  requires_authority: boolean;
  input_schema: Record<string, unknown>;
};

export type VoiceStatus = {
  wake_word: boolean;
  speech_to_text: boolean;
  text_to_speech: boolean;
  speaker_verifier: boolean;
};

export type ActivityEvent = {
  id: string;
  type: string;
  timestamp: string;
  payload: Record<string, unknown>;
};

const API_BASE = import.meta.env.VITE_RUNE_API_URL ?? "http://127.0.0.1:8765";
const SESSION = import.meta.env.VITE_RUNE_SESSION_TOKEN ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(SESSION ? { "X-RUNE-Session": SESSION } : {}),
      ...(init?.headers ?? {}),
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error ?? "RUNE request failed");
  return payload as T;
}

export function getState(): Promise<RuneState> {
  return request<RuneState>("/api/state");
}

export function sendMessage(message: string): Promise<string> {
  return request<{ response: string }>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  }).then((payload) => payload.response);
}

export function getActivity(): Promise<{ events: ActivityEvent[] }> {
  return request<{ events: ActivityEvent[] }>("/api/activity");
}

export function getTools(): Promise<{ tools: ToolSpec[] }> {
  return request<{ tools: ToolSpec[] }>("/api/tools");
}

export function getVoice(): Promise<VoiceStatus> {
  return request<VoiceStatus>("/api/voice");
}

export async function activateWorkspace(id: string) {
  return request("/api/workspace", {
    method: "POST",
    body: JSON.stringify({ workspace_id: id }),
  });
}

export async function controlWindow(operation: string, hwnd: number) {
  return request("/api/window", {
    method: "POST",
    body: JSON.stringify({ operation, hwnd: String(hwnd) }),
  });
}
