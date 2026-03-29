"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useCallback, useEffect, useState } from "react";
import { DiffView } from "@/components/DiffView";
import { JudgeChat } from "@/components/JudgeChat";
import { api, type Prompt, type ReplayJob, type ReplayResult } from "@/lib/api";

export default function ReplayResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [job, setJob] = useState<ReplayJob | null>(null);
  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [promoting, setPromoting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [showPromoteConfirm, setShowPromoteConfirm] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const router = useRouter();

  const fetchJob = useCallback(async () => {
    const j = await api.getReplay(id);
    setJob(j);
    if (!prompt) {
      const p = await api.getPrompt(j.prompt_id);
      setPrompt(p);
    }
    return j;
  }, [id, prompt]);

  useEffect(() => {
    fetchJob();
  }, [fetchJob]);

  // Poll for updates if job is running
  useEffect(() => {
    if (!job || job.status === "complete" || job.status === "failed" || job.status === "stopped") return;
    const interval = setInterval(async () => {
      const j = await fetchJob();
      if (j.status === "complete" || j.status === "failed" || j.status === "stopped") {
        clearInterval(interval);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [job?.status, fetchJob]);

  const sourceVersion = prompt?.versions.find((v) => v.id === job?.source_version_id);
  const targetVersion = prompt?.versions.find((v) => v.id === job?.target_version_id);

  const completedResults =
    job?.results.filter((r) => r.status === "success" || r.status === "failed") || [];
  const successResults = job?.results.filter((r) => r.status === "success") || [];

  const handlePromote = async () => {
    if (!job || !prompt || !targetVersion) return;
    setPromoting(true);
    try {
      await api.promote(prompt.id, targetVersion.id);
      showToastMsg(`v${targetVersion.version_number} is now active`, "success");
      setShowPromoteConfirm(false);
      setTimeout(() => router.push(`/prompts/${prompt.id}`), 1500);
    } catch (err) {
      showToastMsg(err instanceof Error ? err.message : "Failed to promote", "error");
    } finally {
      setPromoting(false);
    }
  };

  const showToastMsg = (message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const getUserMessage = (result: ReplayResult) => {
    if (!result.trace_input) return "—";
    const messages = (result.trace_input as { messages?: { role: string; content: string }[] })
      .messages;
    return messages?.find((m) => m.role === "user")?.content || "—";
  };

  if (!job) {
    return (
      <div className="p-6">
        <div className="h-8 w-96 bg-[var(--color-border-light)] animate-pulse mb-6" />
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 bg-[var(--color-border-light)] animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const handleStop = async () => {
    setStopping(true);
    try {
      await api.stopReplay(id);
      await fetchJob();
    } catch (err) {
      showToastMsg(err instanceof Error ? err.message : "Failed to stop", "error");
    } finally {
      setStopping(false);
    }
  };

  const isRunning = job.status === "running" || job.status === "pending";
  const progress =
    job.trace_count > 0 ? Math.round((completedResults.length / job.trace_count) * 100) : 0;

  return (
    <div className="p-6 pb-24">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 border font-mono text-sm ${
            toast.type === "success"
              ? "bg-[var(--color-success-bg)] border-emerald-200 text-emerald-700"
              : "bg-[var(--color-error-bg)] border-red-200 text-red-700"
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* Promote confirm dialog */}
      {showPromoteConfirm && targetVersion && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] w-[440px] p-6">
            <h2 className="font-mono text-lg font-semibold mb-3">Promote Version</h2>
            <p className="text-sm text-[var(--color-text-muted)] mb-6">
              Promote v{targetVersion.version_number} to active? This replaces{" "}
              {sourceVersion ? `v${sourceVersion.version_number}` : "the current version"} for all
              consumers of this prompt.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowPromoteConfirm(false)}
                className="px-4 py-2 border border-[var(--color-border)] font-mono text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handlePromote}
                disabled={promoting}
                className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium disabled:opacity-50"
              >
                {promoting ? "Promoting..." : "Promote"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Breadcrumb */}
      {prompt && (
        <div className="text-xs font-mono text-[var(--color-text-muted)] mb-2">
          <Link href="/" className="hover:underline hover:text-[var(--color-text-primary)]">Prompts</Link>
          {" / "}
          <Link href={`/prompts/${prompt.id}`} className="hover:underline hover:text-[var(--color-text-primary)]">{prompt.name}</Link>
          {" / "}
          <span>Replay v{sourceVersion?.version_number || "?"} → v{targetVersion?.version_number || "?"}</span>
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <h1 className="font-mono text-[28px] font-semibold">
          {prompt?.name || "Replay"}: v{sourceVersion?.version_number || "?"} → v
          {targetVersion?.version_number || "?"}
        </h1>
        {isRunning && (
          <div className="flex items-center gap-3 mt-1">
            <p className="text-sm text-[var(--color-text-muted)] font-mono">
              {job.status === "pending"
                ? "Starting replay..."
                : `Replaying ${completedResults.length}/${job.trace_count} traces...`}
            </p>
            <button
              type="button"
              onClick={handleStop}
              disabled={stopping}
              className="px-3 py-1 text-xs font-mono border border-red-200 text-red-500 hover:bg-[var(--color-error-bg)] disabled:opacity-50"
            >
              {stopping ? "Stopping..." : "■ Stop"}
            </button>
          </div>
        )}
        {job.status === "complete" && (
          <p className="text-sm text-[var(--color-text-muted)] mt-1 font-mono">
            Replay complete — {job.trace_count}/{job.trace_count} traces processed
          </p>
        )}
        {job.status === "stopped" && (
          <p className="text-sm text-[var(--color-text-muted)] mt-1 font-mono">
            Stopped at {completedResults.length}/{job.trace_count} traces
          </p>
        )}
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="h-2 bg-[var(--color-border-light)] w-full">
          <div
            className="h-2 bg-[var(--color-accent)] transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="font-mono text-xs text-[var(--color-text-muted)]">
            {completedResults.length}/{job.trace_count}
          </span>
          <span className="font-mono text-xs text-[var(--color-text-muted)]">{progress}%</span>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <MetricBox
          label="Improved"
          value={job.improved}
          color="text-emerald-600"
          bg="bg-[var(--color-success-bg)]"
        />
        <MetricBox
          label="Unchanged"
          value={job.unchanged}
          color="text-[var(--color-text-muted)]"
          bg="bg-[var(--color-bg)]"
        />
        <MetricBox
          label="Regressed"
          value={job.regressed}
          color="text-red-500"
          bg="bg-[var(--color-error-bg)]"
        />
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <div className="font-mono text-[48px] font-bold leading-none text-[var(--color-text-primary)]">
            {job.avg_original_score != null && job.avg_replayed_score != null ? (
              <>
                {job.avg_original_score.toFixed(1)}→{job.avg_replayed_score.toFixed(1)}
              </>
            ) : (
              "—"
            )}
          </div>
          <div className="label mt-2">Avg Score</div>
          {job.avg_original_score != null && job.avg_replayed_score != null && (
            <div
              className={`font-mono text-sm mt-1 ${
                job.avg_replayed_score > job.avg_original_score
                  ? "text-emerald-600"
                  : job.avg_replayed_score < job.avg_original_score
                    ? "text-red-500"
                    : "text-[var(--color-text-muted)]"
              }`}
            >
              {job.avg_replayed_score > job.avg_original_score ? "+" : ""}
              {(job.avg_replayed_score - job.avg_original_score).toFixed(1)}
            </div>
          )}
        </div>
      </div>

      {/* Failed count */}
      {job.failed > 0 && (
        <div className="mb-4 px-4 py-2 bg-[var(--color-error-bg)] border border-red-200 text-red-700 font-mono text-sm">
          {successResults.length}/{job.trace_count} succeeded, {job.failed} failed
        </div>
      )}

      {/* Results table (accordion) */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)]">
        <div className="label px-4 py-3 border-b border-[var(--color-border)]">Trace Results</div>
        {job.results.length === 0 ? (
          <div className="p-8 text-center text-[var(--color-text-muted)] text-sm">
            {isRunning ? "Waiting for first result..." : "No results"}
          </div>
        ) : (
          job.results
            .filter((r) => r.status !== "pending" && r.status !== "skipped")
            .map((result, idx) => (
              <div
                key={result.id}
                className={`border-b border-[var(--color-border-light)] ${
                  result.status === "failed" ? "bg-[var(--color-error-bg)]" : ""
                }`}
                style={{ animation: `fadeSlideIn 100ms ease-out ${idx * 50}ms both` }}
              >
                {/* Row header */}
                <div
                  className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-[var(--color-bg)] transition-colors duration-75"
                  onClick={() => setExpanded(expanded === result.id ? null : result.id)}
                >
                  <span className="font-mono text-xs text-[var(--color-text-muted)] w-8">
                    #{idx + 1}
                  </span>
                  <span className={`font-mono text-sm flex-1 ${expanded === result.id ? "" : "truncate"}`}>
                    {expanded === result.id
                      ? getUserMessage(result)
                      : <>
                          {getUserMessage(result).slice(0, 60)}
                          {getUserMessage(result).length > 60 && "..."}
                        </>
                    }
                  </span>
                  {result.status === "success" && result.score_delta != null ? (
                    <span
                      className={`font-mono text-sm font-medium whitespace-nowrap ${
                        result.score_delta > 0
                          ? "text-emerald-600"
                          : result.score_delta < 0
                            ? "text-red-500"
                            : "text-[var(--color-text-muted)]"
                      }`}
                    >
                      {result.original_score}→{result.replayed_score} (
                      {result.score_delta > 0 ? "+" : ""}
                      {result.score_delta}){" "}
                      {result.score_delta > 0 ? "↑" : result.score_delta < 0 ? "↓" : "—"}
                    </span>
                  ) : result.status === "failed" ? (
                    <span className="font-mono text-xs text-red-500">FAILED</span>
                  ) : null}
                  <span className="text-[var(--color-text-muted)]">
                    {expanded === result.id ? "▲" : "▼"}
                  </span>
                </div>

                {/* Expanded content */}
                {expanded === result.id && (
                  <div className="px-4 pb-4">
                    {result.status === "failed" ? (
                      <div className="bg-[var(--color-error-bg)] border border-red-200 p-3 text-sm text-red-700 font-mono">
                        {result.error}
                      </div>
                    ) : (
                      <>
                        <DiffView
                          original={result.original_output}
                          replayed={result.replayed_output}
                          sourceLabel={`v${sourceVersion?.version_number || "?"} (original)`}
                          targetLabel={`v${targetVersion?.version_number || "?"} (replayed)`}
                        />
                        {result.judge_reasoning && sourceVersion && targetVersion && (
                          <JudgeChat
                            jobId={id}
                            resultId={result.id}
                            promptId={job.prompt_id}
                            initialReasoning={result.judge_reasoning}
                            sourceVersion={sourceVersion}
                            targetVersion={targetVersion}
                            activeVersionId={sourceVersion.id}
                          />
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            ))
        )}
      </div>

      {/* Sticky bottom bar - Promote */}
      {(job.status === "complete" || job.status === "stopped") && targetVersion && !targetVersion.is_active && (
        <div className="fixed bottom-0 left-[200px] right-0 bg-[var(--color-surface)] border-t border-[var(--color-border)] p-4 flex justify-center">
          <button
            onClick={() => setShowPromoteConfirm(true)}
            className="px-6 py-3 bg-emerald-600 text-white font-mono text-sm font-semibold hover:bg-emerald-700 transition-colors"
          >
            ↑ Promote v{targetVersion.version_number} to Active
          </button>
        </div>
      )}

      <style jsx>{`
        @keyframes fadeSlideIn {
          from {
            opacity: 0;
            transform: translateY(4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}

function MetricBox({
  label,
  value,
  color,
  bg,
}: {
  label: string;
  value: number;
  color: string;
  bg: string;
}) {
  return (
    <div className={`border border-[var(--color-border)] ${bg} p-4`}>
      <div className={`font-mono text-[48px] font-bold leading-none ${color}`}>{value}</div>
      <div className="label mt-2">{label}</div>
    </div>
  );
}
