"use client";

import { useState } from "react";
import { api, type RerunTraceResponse } from "@/lib/api";

interface JudgeChatProps {
  jobId: string;
  resultId: string;
  promptId: string;
  initialReasoning: string;
  sourceVersion: {
    id: string;
    version_number: number;
    content: string;
    model_config_json: Record<string, unknown>;
  };
  targetVersion: {
    id: string;
    version_number: number;
    content: string;
    model_config_json: Record<string, unknown>;
  };
  activeVersionId: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  suggested_prompt?: string | null;
}

export function JudgeChat({
  jobId,
  resultId,
  promptId,
  initialReasoning,
  sourceVersion,
  targetVersion,
  activeVersionId,
}: JudgeChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Rerun state
  const [rerunning, setRerunning] = useState(false);
  const [rerunResult, setRerunResult] = useState<RerunTraceResponse | null>(null);
  const [rerunError, setRerunError] = useState("");

  // Create version + replay state
  const [creating, setCreating] = useState(false);

  const latestSuggestedPrompt = [...messages]
    .reverse()
    .find((m) => m.suggested_prompt)?.suggested_prompt ?? null;

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMsg: ChatMessage = { role: "user", content: trimmed };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setError("");

    try {
      const apiMessages = nextMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));
      const res = await api.discussJudge(jobId, resultId, apiMessages);
      setMessages([
        ...nextMessages,
        {
          role: "assistant",
          content: res.response,
          suggested_prompt: res.suggested_prompt,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  const handleRerun = async () => {
    if (!latestSuggestedPrompt || rerunning) return;
    setRerunning(true);
    setRerunError("");
    setRerunResult(null);

    try {
      const res = await api.rerunTrace(jobId, resultId, {
        prompt_content: latestSuggestedPrompt,
        model_config: targetVersion.model_config_json,
      });
      setRerunResult(res);
    } catch (err) {
      setRerunError(err instanceof Error ? err.message : "Failed to rerun trace");
    } finally {
      setRerunning(false);
    }
  };

  const handleCreateAndReplay = async () => {
    if (!latestSuggestedPrompt || creating) return;
    setCreating(true);
    setError("");

    try {
      const newVersion = await api.createVersion(promptId, {
        content: latestSuggestedPrompt,
        model_config: targetVersion.model_config_json,
      });
      const newJob = await api.startReplay({
        prompt_id: promptId,
        source_version_id: activeVersionId,
        target_version_id: newVersion.id,
      });
      window.location.href = `/replay/${newJob.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create version and start replay");
      setCreating(false);
    }
  };

  return (
    <div className="mt-3 border border-[var(--color-border)] bg-[var(--color-surface)]">
      {/* Initial reasoning */}
      <div className="px-4 py-3 border-b border-[var(--color-border)]">
        <div className="label mb-2">Judge Reasoning</div>
        <div className="text-sm text-[var(--color-text-muted)] whitespace-pre-wrap">
          {initialReasoning}
        </div>
      </div>

      {/* Chat messages */}
      {messages.length > 0 && (
        <div className="border-b border-[var(--color-border)]">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`px-4 py-3 ${
                i < messages.length - 1 ? "border-b border-[var(--color-border-light)]" : ""
              } ${msg.role === "user" ? "bg-[var(--color-bg)]" : ""}`}
            >
              <div className="label mb-1 text-xs">
                {msg.role === "user" ? "You" : "Judge"}
              </div>
              <div className="text-sm whitespace-pre-wrap">{msg.content}</div>

              {/* Suggested prompt block */}
              {msg.suggested_prompt && (
                <div className="mt-3 border border-[var(--color-accent)] bg-[var(--color-bg)]">
                  <div className="px-3 py-2 border-b border-[var(--color-accent)] bg-[var(--color-accent)]/10">
                    <span className="label text-xs text-[var(--color-accent)]">
                      Suggested Prompt
                    </span>
                  </div>
                  <pre className="px-3 py-3 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
                    {msg.suggested_prompt}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="mx-4 mt-3 px-3 py-2 bg-[var(--color-error-bg)] border border-red-200 text-red-700 text-sm font-mono">
          {error}
        </div>
      )}

      {/* Chat input */}
      <div className="px-4 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Discuss the reasoning with the judge..."
            disabled={loading}
            className="flex-1 px-3 py-2 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm focus:outline-none focus:border-[var(--color-accent)] disabled:opacity-50"
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-[var(--color-accent)] text-white font-mono text-sm font-medium disabled:opacity-50"
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>

      {/* Action buttons — only when a suggested prompt exists */}
      {latestSuggestedPrompt && (
        <div className="px-4 pb-4">
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleRerun}
              disabled={rerunning || creating}
              className="px-4 py-2 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm hover:bg-[var(--color-surface)] disabled:opacity-50"
            >
              {rerunning ? "Rerunning..." : "Rerun This Trace"}
            </button>
            <button
              type="button"
              onClick={handleCreateAndReplay}
              disabled={creating || rerunning}
              className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create Version & Replay All"}
            </button>
          </div>

          {/* Rerun error */}
          {rerunError && (
            <div className="mt-3 px-3 py-2 bg-[var(--color-error-bg)] border border-red-200 text-red-700 text-sm font-mono">
              {rerunError}
            </div>
          )}

          {/* Rerun result inline */}
          {rerunResult && (
            <div className="mt-3 border border-[var(--color-border)] bg-[var(--color-bg)]">
              <div className="px-4 py-3 border-b border-[var(--color-border)]">
                <span className="label">Rerun Result</span>
              </div>
              <div className="px-4 py-3">
                {/* Scores */}
                <div className="flex gap-6 mb-3">
                  <div>
                    <span className="label text-xs">Original Score</span>
                    <div className="font-mono text-lg font-semibold">
                      {rerunResult.original_score ?? "—"}
                    </div>
                  </div>
                  <div>
                    <span className="label text-xs">Replayed Score</span>
                    <div className="font-mono text-lg font-semibold">
                      {rerunResult.replayed_score ?? "—"}
                    </div>
                  </div>
                  {rerunResult.score_delta != null && (
                    <div>
                      <span className="label text-xs">Delta</span>
                      <div
                        className={`font-mono text-lg font-semibold ${
                          rerunResult.score_delta > 0
                            ? "text-emerald-600"
                            : rerunResult.score_delta < 0
                              ? "text-red-500"
                              : "text-[var(--color-text-muted)]"
                        }`}
                      >
                        {rerunResult.score_delta > 0 ? "+" : ""}
                        {rerunResult.score_delta}
                      </div>
                    </div>
                  )}
                </div>

                {/* Judge reasoning for the rerun */}
                {rerunResult.judge_reasoning && (
                  <div>
                    <div className="label text-xs mb-1">Judge Reasoning</div>
                    <div className="text-sm text-[var(--color-text-muted)] whitespace-pre-wrap">
                      {rerunResult.judge_reasoning}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
