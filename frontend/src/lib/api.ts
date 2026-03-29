const API_BASE = typeof window !== "undefined" ? "/api" : "http://backend:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    credentials: "include",
    ...options,
  });
  if (res.status === 401 && typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
    throw new Error("Not authenticated");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export interface AuthUser {
  email: string;
  api_key: string;
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
  prompt_name: string | null;
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
  prompt_name: string;
  source_version_number: number | null;
  target_version_number: number | null;
}

export interface JudgeDiscussResponse {
  response: string;
  suggested_prompt: string | null;
}

export interface RerunTraceResponse {
  original_output: string;
  replayed_output: string;
  original_score: number | null;
  replayed_score: number | null;
  score_delta: number | null;
  judge_reasoning: string;
}

export interface PlaygroundResponse {
  output: string;
  latency_ms: number;
}

export interface ScenarioItem {
  role: string;
  message: string;
  variables: Record<string, string>;
}

export interface ScenarioJobItem {
  id: string;
  status: string;
  role: string;
  message: string;
  trace_id: string | null;
  output_preview: string;
  latency_ms: number;
  error: string | null;
}

export interface ScenarioJob {
  id: string;
  prompt_id: string;
  prompt_version_id: string;
  status: string;
  total: number;
  completed: number;
  created_at: string;
  completed_at: string | null;
  items: ScenarioJobItem[];
}

export const api = {
  // Auth
  getMe: () => request<AuthUser>("/auth/me"),
  logout: () =>
    fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" }).then(() => {
      window.location.href = "/login";
    }),

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
  updateVersion: (
    promptId: string,
    versionId: string,
    data: { content: string; model_config: Record<string, unknown> },
  ) =>
    request<PromptVersion>(`/prompts/${promptId}/versions/${versionId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  promote: (promptId: string, versionId: string) =>
    request<PromptVersion>(`/prompts/${promptId}/promote`, {
      method: "POST",
      body: JSON.stringify({ version_id: versionId }),
    }),
  deletePrompt: (id: string) =>
    request<{ status: string }>(`/prompts/${id}`, { method: "DELETE" }),
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
  stopReplay: (jobId: string) =>
    request<{ status: string }>(`/replay/${jobId}/stop`, { method: "POST" }),
  listReplays: (promptId?: string) =>
    request<ReplayJob[]>(`/replays${promptId ? `?prompt_id=${promptId}` : ""}`),

  // Scenarios
  generateScenarios: (promptId: string, data: { description: string; count: number; version_id?: string }) =>
    request<{ scenarios: ScenarioItem[] }>(`/prompts/${promptId}/generate-scenarios`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  runScenarios: (promptId: string, data: { scenarios: ScenarioItem[]; version_id?: string }) =>
    request<{ job_id: string }>(`/prompts/${promptId}/run-scenarios`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getScenarioJob: (jobId: string) => request<ScenarioJob>(`/scenario-jobs/${jobId}`),

  // Judge chat
  discussJudge: (jobId: string, resultId: string, messages: { role: string; content: string }[]) =>
    request<JudgeDiscussResponse>(`/replay/${jobId}/results/${resultId}/discuss`, {
      method: "POST",
      body: JSON.stringify({ messages }),
    }),
  rerunTrace: (
    jobId: string,
    resultId: string,
    data: { prompt_content: string; model_config?: Record<string, unknown> },
  ) =>
    request<RerunTraceResponse>(`/replay/${jobId}/results/${resultId}/rerun`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
