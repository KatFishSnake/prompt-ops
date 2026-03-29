"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api, type Trace, type PromptListItem } from "@/lib/api";

function TracesContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialPromptId = searchParams.get("prompt_id") || "";

  const [traces, setTraces] = useState<Trace[]>([]);
  const [prompts, setPrompts] = useState<PromptListItem[]>([]);
  const [selectedPromptId, setSelectedPromptId] = useState(initialPromptId);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchTraces = useCallback((promptId: string) => {
    setLoading(true);
    api
      .listTraces(promptId || undefined)
      .then(setTraces)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    api.listPrompts().then(setPrompts);
  }, []);

  useEffect(() => {
    fetchTraces(selectedPromptId);
  }, [selectedPromptId, fetchTraces]);

  const handleFilterChange = (promptId: string) => {
    setSelectedPromptId(promptId);
    setExpanded(null);
    const params = new URLSearchParams(searchParams.toString());
    if (promptId) {
      params.set("prompt_id", promptId);
    } else {
      params.delete("prompt_id");
    }
    router.replace(`/traces${params.toString() ? `?${params.toString()}` : ""}`);
  };

  const getUserMessage = (trace: Trace) => {
    const messages = (trace.input as { messages?: { role: string; content: string }[] }).messages;
    const userMsg = messages?.find((m) => m.role === "user");
    return userMsg?.content || "—";
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="font-mono text-[28px] font-semibold">Traces</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">Real input/output pairs captured from your production AI calls.</p>
      </div>

      <div className="mb-4">
        <label className="label mr-3">Filter by prompt</label>
        <select
          value={selectedPromptId}
          onChange={(e) => handleFilterChange(e.target.value)}
          className="font-mono text-sm bg-[var(--color-surface)] border border-[var(--color-border)] px-3 py-2 text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
          style={{ borderRadius: 0 }}
        >
          <option value="">All Prompts</option>
          {prompts.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-[var(--color-border-light)] animate-pulse" />
          ))}
        </div>
      ) : traces.length === 0 ? (
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] p-8">
          <p className="font-mono text-lg mb-2">No traces ingested yet</p>
          <p className="text-[var(--color-text-muted)] text-sm mb-4">
            Send traces via POST /api/traces to see them here.
          </p>
          <pre className="bg-[var(--color-bg)] border border-[var(--color-border)] p-4 text-xs font-mono overflow-x-auto">
            {`curl -X POST http://localhost:8000/api/traces \\
  -H "Content-Type: application/json" \\
  -d '{"traces": [{"prompt_name": "my-prompt", "input": {"messages": [{"role": "user", "content": "Hello"}]}, "output": "Hi there!", "model": "gpt-4o-mini"}]}'`}
          </pre>
        </div>
      ) : (
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="label text-left py-3 px-4">Input</th>
                <th className="label text-left py-3 px-4">Prompt</th>
                <th className="label text-left py-3 px-4">Model</th>
                <th className="label text-right py-3 px-4">Latency</th>
                <th className="label text-left py-3 px-4">Time</th>
              </tr>
            </thead>
            <tbody>
              {traces.map((trace) => (
                <tr key={trace.id} className="border-b border-[var(--color-border-light)]">
                  <td className="py-3 px-4" colSpan={expanded === trace.id ? 5 : 1}>
                    <div
                      className="cursor-pointer"
                      onClick={() => setExpanded(expanded === trace.id ? null : trace.id)}
                    >
                      <div className={`font-mono text-sm ${expanded === trace.id ? "" : "truncate max-w-[500px]"}`}>
                        {expanded === trace.id
                          ? getUserMessage(trace)
                          : <>
                              {getUserMessage(trace).slice(0, 80)}
                              {getUserMessage(trace).length > 80 && "..."}
                            </>
                        }
                      </div>
                      {expanded === trace.id && (
                        <div className="mt-4 space-y-4">
                          <div>
                            <div className="label mb-2">Input</div>
                            <pre className="bg-[var(--color-bg)] border border-[var(--color-border)] p-3 text-xs font-mono overflow-x-auto max-h-48 overflow-y-auto">
                              {JSON.stringify(trace.input, null, 2)}
                            </pre>
                          </div>
                          <div>
                            <div className="label mb-2">Output</div>
                            <div className="bg-[var(--color-bg)] border border-[var(--color-border)] p-3 text-sm whitespace-pre-wrap">
                              {trace.output}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </td>
                  {expanded !== trace.id && (
                    <>
                      <td className="py-3 px-4 font-mono text-xs text-[var(--color-text-muted)]">
                        {trace.prompt_id ? (
                          <Link
                            href={`/prompts/${trace.prompt_id}`}
                            className="hover:underline hover:text-[var(--color-text-primary)]"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {trace.prompt_name || "—"}
                          </Link>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-[var(--color-text-muted)]">
                        {trace.model}
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-right text-[var(--color-text-muted)]">
                        {trace.latency_ms}ms
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-[var(--color-text-muted)]">
                        {new Date(trace.created_at).toLocaleString()}
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function TracesPage() {
  return (
    <Suspense
      fallback={
        <div className="p-6">
          <div className="mb-6">
            <h1 className="font-mono text-[28px] font-semibold">Traces</h1>
            <p className="text-sm text-[var(--color-text-muted)] mt-1">Real input/output pairs captured from your production AI calls.</p>
          </div>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 bg-[var(--color-border-light)] animate-pulse" />
            ))}
          </div>
        </div>
      }
    >
      <TracesContent />
    </Suspense>
  );
}
