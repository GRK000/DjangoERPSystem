export type AgentStatus = {
  available: boolean;
  provider: string;
  model: string;
  missing_api_key: boolean;
  mock_mode: boolean;
  real_llm_enabled: boolean;
};

export type AgentMessage = {
  id?: number;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
};

export type AgentConversation = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: AgentMessage[];
};

export type AgentEvidence = {
  type: string;
  label: string;
  url?: string;
  metadata?: Record<string, unknown>;
};

export type AgentSuggestedAction = {
  type: "navigate" | "filter" | "inspect";
  label: string;
  target: string;
  params?: Record<string, unknown>;
};

export type AgentToolCall = {
  name: string;
  status: string;
};

export type AgentRunResponse = {
  conversation_id: number;
  run_id: number;
  answer: string;
  evidence: AgentEvidence[];
  suggested_actions: AgentSuggestedAction[];
  tool_calls: AgentToolCall[];
  status: "ok" | "blocked" | "error";
};

export async function agentGet<T>(url: string): Promise<T> {
  const response = await fetch(url, { credentials: "same-origin" });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function agentPost<T>(url: string, csrfToken: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

async function readError(response: Response) {
  try {
    const payload = await response.json();
    return payload.detail || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}
