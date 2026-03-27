const API_BASE = typeof window !== "undefined" ? "/api" : "http://backend:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export interface PromptVersion {
  id: string;
  prompt_id: string;
  version_number: number;
  content: string;
  model_config_json: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  created_by: string;
}

export interface Prompt {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  versions: PromptVersion[];
}

export interface PromptListItem {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  version_count: number;
  active_version: number | null;
  latest_replay: {
    job_id: string;
    source_version_id: string;
    target_version_id: string;
    improved: number;
    regressed: number;
    unchanged: number;
  } | null;
}

export interface Trace {
  id: string;
  prompt_id: string | null;
  prompt_version_id: string | null;
  input: Record<string, unknown>;
  output: string;
  model: string;
  latency_ms: number;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface ReplayResult {
  id: string;
  replay_job_id: string;
  trace_id: string;
  status: string;
  original_output: string;
  replayed_output: string;
  original_score: number | null;
  replayed_score: number | null;
  score_delta: number | null;
  judge_reasoning: string;
  error: string | null;
  completed_at: string | null;
  trace_input: Record<string, unknown> | null;
}

export interface ReplayJob {
  id: string;
  prompt_id: string;
  source_version_id: string;
  target_version_id: string;
  status: string;
  trace_count: number;
  created_at: string;
  completed_at: string | null;
  results: ReplayResult[];
  improved: number;
  unchanged: number;
  regressed: number;
  failed: number;
  avg_original_score: number | null;
  avg_replayed_score: number | null;
}

export interface PlaygroundResponse {
  output: string;
  latency_ms: number;
}

export const api = {
  // Prompts
  listPrompts: () => request<PromptListItem[]>("/prompts"),
  getPrompt: (id: string) => request<Prompt>(`/prompts/${id}`),
  createPrompt: (data: { name: string; description: string }) =>
    request<Prompt>("/prompts", { method: "POST", body: JSON.stringify(data) }),
  createVersion: (
    promptId: string,
    data: { content: string; model_config: Record<string, unknown> },
  ) =>
    request<PromptVersion>(`/prompts/${promptId}/versions`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  promote: (promptId: string, versionId: string) =>
    request<PromptVersion>(`/prompts/${promptId}/promote`, {
      method: "POST",
      body: JSON.stringify({ version_id: versionId }),
    }),
  playground: (
    promptId: string,
    data: {
      content: string;
      variables: Record<string, string>;
      user_message: string;
      model_config: Record<string, unknown>;
    },
  ) =>
    request<PlaygroundResponse>(`/prompts/${promptId}/playground`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Traces
  listTraces: (promptId?: string) =>
    request<Trace[]>(`/traces${promptId ? `?prompt_id=${promptId}` : ""}`),

  // Replay
  startReplay: (data: {
    prompt_id: string;
    source_version_id: string;
    target_version_id: string;
  }) => request<ReplayJob>("/replay", { method: "POST", body: JSON.stringify(data) }),
  getReplay: (jobId: string) => request<ReplayJob>(`/replay/${jobId}`),
  listReplays: (promptId?: string) =>
    request<ReplayJob[]>(`/replays${promptId ? `?prompt_id=${promptId}` : ""}`),
};
