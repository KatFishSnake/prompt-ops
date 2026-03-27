"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type ScenarioItem, type ScenarioJob } from "@/lib/api";

const STORAGE_KEY_PREFIX = "promptops-scenarios-";

export function ScenarioBuilder({
  promptId,
  activeVersionNumber,
}: {
  promptId: string;
  activeVersionNumber: number | null;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [description, setDescription] = useState("");
  const [count, setCount] = useState(10);
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<ScenarioJob | null>(null);
  const [editIdx, setEditIdx] = useState<number | null>(null);
  const [editMessage, setEditMessage] = useState("");
  const [customMessage, setCustomMessage] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load scenarios from localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY_PREFIX + promptId);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (parsed.scenarios) setScenarios(parsed.scenarios);
        if (parsed.description) setDescription(parsed.description);
      } catch {}
    }
  }, [promptId]);

  // Save scenarios to localStorage
  useEffect(() => {
    if (scenarios.length > 0) {
      localStorage.setItem(
        STORAGE_KEY_PREFIX + promptId,
        JSON.stringify({ scenarios, description }),
      );
    }
  }, [scenarios, description, promptId]);

  // Poll for job progress
  const pollJob = useCallback(
    async (id: string) => {
      try {
        const j = await api.getScenarioJob(id);
        setJob(j);
        if (j.status === "complete" || j.status === "failed") {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }
      } catch {}
    },
    [],
  );

  useEffect(() => {
    if (!jobId) return;
    pollJob(jobId);
    pollRef.current = setInterval(() => pollJob(jobId), 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId, pollJob]);

  const handleGenerate = async () => {
    if (!description.trim()) return;
    setGenerating(true);
    setError("");
    try {
      const res = await api.generateScenarios(promptId, { description, count });
      setScenarios(res.scenarios);
      setJobId(null);
      setJob(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate scenarios");
    } finally {
      setGenerating(false);
    }
  };

  const handleRunAll = async () => {
    if (scenarios.length === 0) return;
    setError("");
    try {
      const res = await api.runScenarios(promptId, { scenarios });
      setJobId(res.job_id);
      setJob(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start scenario run");
    }
  };

  const removeScenario = (idx: number) => {
    setScenarios(scenarios.filter((_, i) => i !== idx));
  };

  const startEdit = (idx: number) => {
    setEditIdx(idx);
    setEditMessage(scenarios[idx].message);
  };

  const saveEdit = () => {
    if (editIdx === null) return;
    const updated = [...scenarios];
    updated[editIdx] = { ...updated[editIdx], message: editMessage };
    setScenarios(updated);
    setEditIdx(null);
  };

  const addCustom = () => {
    if (!customMessage.trim()) return;
    setScenarios([...scenarios, { role: "Custom", message: customMessage, variables: {} }]);
    setCustomMessage("");
  };

  const isRunning = job && (job.status === "running" || job.status === "pending");
  const isComplete = job?.status === "complete";
  const completedCount = job?.completed ?? 0;

  if (!activeVersionNumber) {
    return (
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mt-4">
        <div className="px-4 py-3">
          <span className="label">Generate Test Scenarios</span>
        </div>
        <div className="border-t border-[var(--color-border)] p-4">
          <p className="text-sm text-[var(--color-text-muted)]">
            Promote a version to active before generating scenarios.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mt-4">
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-[var(--color-bg)] transition-colors duration-75"
      >
        <span className="label">Generate Test Scenarios</span>
        <span className="text-[var(--color-text-muted)]">{collapsed ? "▼" : "▲"}</span>
      </button>

      {!collapsed && (
        <div className="border-t border-[var(--color-border)]">
          {/* Description input */}
          <div className="p-4">
            <p className="text-xs text-[var(--color-text-muted)] mb-3">
              Describe your use case and we'll generate diverse test scenarios to evaluate your
              prompt. Scenarios run against v{activeVersionNumber} (active).
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !generating && handleGenerate()}
                placeholder="e.g. Customer support agent for a SaaS billing platform"
                className="flex-1 px-3 py-2 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm focus:outline-none focus:border-[var(--color-accent)]"
                disabled={!!isRunning}
              />
              <div className="flex items-center gap-1">
                <select
                  value={count}
                  onChange={(e) => setCount(Number(e.target.value))}
                  className="px-2 py-2 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm"
                  disabled={!!isRunning}
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                </select>
              </div>
              <button
                type="button"
                onClick={handleGenerate}
                disabled={generating || !description.trim() || !!isRunning}
                className="px-4 py-2 bg-[var(--color-accent)] text-white font-mono text-sm font-medium disabled:opacity-50 whitespace-nowrap"
              >
                {generating ? "Generating..." : "Generate Scenarios"}
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="mx-4 mb-4 px-3 py-2 bg-[var(--color-error-bg)] border border-red-200 text-red-700 text-sm font-mono">
              {error}
            </div>
          )}

          {/* Scenario list */}
          {scenarios.length > 0 && !isRunning && !isComplete && (
            <div className="border-t border-[var(--color-border)]">
              <div className="divide-y divide-[var(--color-border-light)]">
                {scenarios.map((s, idx) => (
                  <div key={idx} className="flex items-start gap-3 px-4 py-3">
                    <span className="font-mono text-xs text-[var(--color-text-muted)] min-w-[24px] pt-0.5">
                      #{idx + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-mono font-medium text-[var(--color-accent)] mb-1">
                        {s.role}
                      </div>
                      {editIdx === idx ? (
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={editMessage}
                            onChange={(e) => setEditMessage(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && saveEdit()}
                            className="flex-1 px-2 py-1 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm focus:outline-none focus:border-[var(--color-accent)]"
                            autoFocus
                          />
                          <button
                            type="button"
                            onClick={saveEdit}
                            className="px-2 py-1 text-xs font-mono border border-[var(--color-border)] hover:bg-[var(--color-bg)]"
                          >
                            Save
                          </button>
                        </div>
                      ) : (
                        <div className="font-mono text-sm leading-relaxed">{s.message}</div>
                      )}
                      {Object.keys(s.variables).length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {Object.entries(s.variables).map(([k, v]) => (
                            <span
                              key={k}
                              className="inline-block text-[10px] px-1.5 py-0.5 bg-[var(--color-info-bg)] border border-blue-200 text-blue-700 font-mono"
                            >
                              {`{{${k}}}`} = "{v}"
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <button
                        type="button"
                        onClick={() => startEdit(idx)}
                        className="px-2 py-1 text-[10px] font-mono border border-[var(--color-border)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg)]"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => removeScenario(idx)}
                        className="px-2 py-1 text-[10px] font-mono border border-red-200 text-red-500 hover:bg-[var(--color-error-bg)]"
                      >
                        x
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Add custom */}
              <div className="flex gap-2 px-4 py-3 border-t border-[var(--color-border-light)]">
                <input
                  type="text"
                  value={customMessage}
                  onChange={(e) => setCustomMessage(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addCustom()}
                  placeholder="Add a custom scenario..."
                  className="flex-1 px-2 py-1 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-xs focus:outline-none focus:border-[var(--color-accent)]"
                />
                <button
                  type="button"
                  onClick={addCustom}
                  disabled={!customMessage.trim()}
                  className="px-3 py-1 text-xs font-mono border border-[var(--color-border)] hover:bg-[var(--color-bg)] disabled:opacity-50"
                >
                  + Add
                </button>
              </div>

              {/* Run bar */}
              <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--color-border)] bg-[var(--color-bg)]">
                <span className="text-xs text-[var(--color-text-muted)] font-mono">
                  {scenarios.length} scenarios · v{activeVersionNumber} (active)
                </span>
                <button
                  type="button"
                  onClick={handleRunAll}
                  className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium"
                >
                  ▶ Run All & Generate Traces
                </button>
              </div>
            </div>
          )}

          {/* Running state */}
          {isRunning && job && (
            <div className="border-t border-[var(--color-border)] p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="label">Generating Traces</span>
                <span className="text-xs font-mono text-[var(--color-accent)]">
                  {completedCount} / {job.total} complete
                </span>
              </div>
              <div className="h-1 bg-[var(--color-border-light)] mb-4">
                <div
                  className="h-1 bg-[var(--color-accent)] transition-all duration-300"
                  style={{ width: `${job.total > 0 ? (completedCount / job.total) * 100 : 0}%` }}
                />
              </div>
              <div className="border border-[var(--color-border)] divide-y divide-[var(--color-border-light)]">
                {job.items.map((item) => (
                  <div key={item.id} className="flex items-center gap-3 px-4 py-2.5">
                    <span
                      className={`w-2 h-2 ${
                        item.status === "success"
                          ? "bg-emerald-500"
                          : item.status === "running"
                            ? "bg-[var(--color-accent)]"
                            : item.status === "failed"
                              ? "bg-red-500"
                              : "bg-[var(--color-border)]"
                      }`}
                    />
                    <span className="flex-1 font-mono text-xs truncate">
                      {item.message.slice(0, 80)}
                      {item.message.length > 80 && "..."}
                    </span>
                    {item.status === "success" && (
                      <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
                        {item.latency_ms}ms
                      </span>
                    )}
                    {item.status === "running" && (
                      <span className="text-[10px] font-mono text-[var(--color-accent)]">...</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Complete state */}
          {isComplete && job && (
            <div className="border-t border-[var(--color-border)]">
              <div className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="label">{job.total} Traces Generated</span>
                  <span className="text-xs font-mono font-medium text-emerald-600">
                    ✓ Complete
                  </span>
                </div>
                <div className="border border-[var(--color-border)] divide-y divide-[var(--color-border-light)]">
                  {job.items.map((item) => (
                    <div key={item.id} className="flex items-center gap-3 px-4 py-2.5">
                      <span
                        className={`w-2 h-2 ${item.status === "success" ? "bg-emerald-500" : "bg-red-500"}`}
                      />
                      <span className="font-mono text-xs text-[var(--color-accent)] min-w-[100px]">
                        {item.role}
                      </span>
                      <span className="flex-1 font-mono text-xs truncate">
                        {item.message.slice(0, 60)}
                        {item.message.length > 60 && "..."}
                      </span>
                      <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
                        {item.status === "success" ? `${item.latency_ms}ms` : "failed"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--color-border)] bg-[var(--color-bg)]">
                <span className="text-xs text-[var(--color-text-muted)] font-mono">
                  Traces saved to v{activeVersionNumber} (active)
                </span>
                <div className="flex gap-2">
                  <a
                    href="/traces"
                    className="px-3 py-2 text-xs font-mono border border-[var(--color-border)] hover:bg-[var(--color-surface)]"
                  >
                    View in Traces →
                  </a>
                  <button
                    type="button"
                    onClick={() => {
                      setJobId(null);
                      setJob(null);
                      setScenarios([]);
                      localStorage.removeItem(STORAGE_KEY_PREFIX + promptId);
                    }}
                    className="px-3 py-2 text-xs font-mono bg-[var(--color-accent)] text-white font-medium"
                  >
                    Generate More
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Empty state */}
          {scenarios.length === 0 && !generating && !isRunning && !isComplete && !error && (
            <div className="border-t border-[var(--color-border)] p-4">
              <p className="text-sm text-[var(--color-text-muted)] italic">
                Describe your use case above and click Generate to create test scenarios.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
