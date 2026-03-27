"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function Playground({
  promptId,
  content,
  variables,
  modelConfig,
}: {
  promptId: string;
  content: string;
  variables: string[];
  modelConfig: { model: string; temperature: number; max_tokens: number };
}) {
  const [varValues, setVarValues] = useState<Record<string, string>>({});
  const [userMessage, setUserMessage] = useState("");
  const [response, setResponse] = useState<{ output: string; latency_ms: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [collapsed, setCollapsed] = useState(true);

  const handleSend = async () => {
    if (!userMessage.trim()) return;
    setLoading(true);
    setError("");
    setResponse(null);
    try {
      const res = await api.playground(promptId, {
        content,
        variables: varValues,
        user_message: userMessage,
        model_config: modelConfig,
      });
      setResponse(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run playground");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      id="playground"
      className="border border-[var(--color-border)] bg-[var(--color-surface)] mt-4"
    >
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-[var(--color-bg)] transition-colors duration-75"
      >
        <span className="label">Playground</span>
        <span className="text-[var(--color-text-muted)]">{collapsed ? "▼" : "▲"}</span>
      </button>

      {!collapsed && (
        <div className="border-t border-[var(--color-border)] p-4">
          {variables.length > 0 && (
            <div className="mb-4">
              <div className="label mb-2">Variables</div>
              <div className="flex flex-wrap gap-3">
                {variables.map((v) => (
                  <div key={v} className="flex items-center gap-2">
                    <span className="font-mono text-xs text-[var(--color-text-muted)]">{`{{${v}}}`}</span>
                    <input
                      type="text"
                      value={varValues[v] || ""}
                      onChange={(e) => setVarValues({ ...varValues, [v]: e.target.value })}
                      placeholder={v}
                      className="w-40 px-2 py-1 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm focus:outline-none focus:border-[var(--color-accent)]"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mb-4">
            <div className="label mb-2">User Message</div>
            <div className="flex gap-2">
              <input
                type="text"
                value={userMessage}
                onChange={(e) => setUserMessage(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="Type a message to test the prompt..."
                className="flex-1 px-3 py-2 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm focus:outline-none focus:border-[var(--color-accent)]"
              />
              <button
                type="button"
                onClick={handleSend}
                disabled={loading || !userMessage.trim()}
                className="px-4 py-2 bg-[var(--color-accent)] text-white font-mono text-sm font-medium disabled:opacity-50"
              >
                {loading ? "..." : "▶ Send"}
              </button>
            </div>
          </div>

          {error && (
            <div className="px-3 py-2 bg-[var(--color-error-bg)] border border-red-200 text-red-700 text-sm font-mono">
              {error}
            </div>
          )}

          {response && (
            <div className="mt-3">
              <div className="label mb-2">Response</div>
              <div className="bg-[var(--color-bg)] border border-[var(--color-border)] p-3 text-sm whitespace-pre-wrap">
                {response.output}
              </div>
              <div className="mt-1 text-xs text-[var(--color-text-muted)] font-mono">
                {response.latency_ms}ms
              </div>
            </div>
          )}

          {!response && !error && !loading && (
            <div className="text-sm text-[var(--color-text-muted)] italic">
              Try your prompt. Type a message and click Send.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
