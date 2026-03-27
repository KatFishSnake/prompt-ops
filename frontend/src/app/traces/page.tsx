"use client";

import { useEffect, useState } from "react";
import { api, type Trace } from "@/lib/api";

export default function TracesPage() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    api
      .listTraces()
      .then(setTraces)
      .finally(() => setLoading(false));
  }, []);

  const getUserMessage = (trace: Trace) => {
    const messages = (trace.input as { messages?: { role: string; content: string }[] }).messages;
    const userMsg = messages?.find((m) => m.role === "user");
    return userMsg?.content || "—";
  };

  const getPromptName = (trace: Trace) => {
    const input = trace.input as {
      messages?: { role: string; content: string }[];
      template_vars?: Record<string, string>;
    };
    return input.template_vars?.product_name || "—";
  };

  return (
    <div className="p-6">
      <h1 className="font-mono text-[28px] font-semibold mb-6">Traces</h1>

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
                <th className="label text-left py-3 px-4">Model</th>
                <th className="label text-right py-3 px-4">Latency</th>
                <th className="label text-left py-3 px-4">Time</th>
              </tr>
            </thead>
            <tbody>
              {traces.map((trace) => (
                <tr key={trace.id} className="border-b border-[var(--color-border-light)]">
                  <td className="py-3 px-4" colSpan={expanded === trace.id ? 4 : 1}>
                    <div
                      className="cursor-pointer"
                      onClick={() => setExpanded(expanded === trace.id ? null : trace.id)}
                    >
                      <div className="font-mono text-sm truncate max-w-[500px]">
                        {getUserMessage(trace).slice(0, 80)}
                        {getUserMessage(trace).length > 80 && "..."}
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
