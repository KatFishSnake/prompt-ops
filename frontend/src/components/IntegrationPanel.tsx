"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function IntegrationPanel({ promptName }: { promptName: string }) {
  const [collapsed, setCollapsed] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string>("");

  useEffect(() => {
    api.getMe().then((u) => setApiKey(u.api_key)).catch(() => {});
  }, []);

  const origin = typeof window !== "undefined" ? window.location.origin : "http://localhost:8000";
  const apiBase = origin.includes("3000") ? origin.replace("3000", "8000") : origin;

  const serveUrl = `${apiBase}/api/prompts/serve/${promptName}`;
  const traceSnippet = `curl -X POST ${apiBase}/api/traces \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: ${apiKey || "YOUR_API_KEY"}" \\
  -d '{"traces": [{"prompt_name": "${promptName}", "input": {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "Hello"}], "template_vars": {}}, "output": "Response here", "model": "gpt-4o-mini", "latency_ms": 500}]}'`;

  const pythonSnippet = `import requests

HEADERS = {"X-API-Key": "${apiKey || "YOUR_API_KEY"}"}

# Fetch the active prompt
prompt = requests.get("${serveUrl}", headers=HEADERS).json()
print(prompt["content"])  # Your prompt template

# After calling your LLM, send the trace back
requests.post("${apiBase}/api/traces", headers=HEADERS, json={"traces": [{
    "prompt_name": "${promptName}",
    "input": {"messages": [...], "template_vars": {...}},
    "output": "LLM response",
    "model": "gpt-4o-mini",
    "latency_ms": 500
}]})`;

  const copy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mt-4">
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-[var(--color-bg)] transition-colors duration-75"
      >
        <span className="label">Integrate</span>
        <span className="text-[var(--color-text-muted)]">{collapsed ? "▼" : "▲"}</span>
      </button>

      {!collapsed && (
        <div className="border-t border-[var(--color-border)] p-4 space-y-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="label">Serve This Prompt</div>
              <button
                type="button"
                onClick={() => copy(serveUrl, "serve")}
                className="text-xs font-mono text-[var(--color-accent)] hover:underline"
              >
                {copied === "serve" ? "Copied!" : "Copy"}
              </button>
            </div>
            <pre className="bg-[var(--color-bg)] border border-[var(--color-border)] p-3 text-xs font-mono overflow-x-auto">
              GET {serveUrl}
            </pre>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">
              Your app calls this at runtime to get the active prompt version.
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="label">Send Traces</div>
              <button
                type="button"
                onClick={() => copy(traceSnippet, "trace")}
                className="text-xs font-mono text-[var(--color-accent)] hover:underline"
              >
                {copied === "trace" ? "Copied!" : "Copy"}
              </button>
            </div>
            <pre className="bg-[var(--color-bg)] border border-[var(--color-border)] p-3 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
              {traceSnippet}
            </pre>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">
              After your app calls the LLM, send the input/output pair back as a trace.
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="label">Python Example</div>
              <button
                type="button"
                onClick={() => copy(pythonSnippet, "python")}
                className="text-xs font-mono text-[var(--color-accent)] hover:underline"
              >
                {copied === "python" ? "Copied!" : "Copy"}
              </button>
            </div>
            <pre className="bg-[var(--color-bg)] border border-[var(--color-border)] p-3 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
              {pythonSnippet}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
