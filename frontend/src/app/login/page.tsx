"use client";

import { useState } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/auth/magic-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
        credentials: "include",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(data.detail || "Request failed");
      }
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
      <div className="w-[400px] border border-[var(--color-border)] bg-[var(--color-surface)] p-8">
        <h1 className="font-mono text-2xl font-bold mb-2">PromptOps</h1>
        <p className="text-sm text-[var(--color-text-muted)] mb-8">
          Prompt management and replay platform
        </p>

        {sent ? (
          <div>
            <div className="px-4 py-3 bg-[var(--color-success-bg)] border border-emerald-200 text-emerald-700 font-mono text-sm mb-4">
              Check your email for a login link.
            </div>
            <p className="text-xs text-[var(--color-text-muted)]">
              Sent to <strong className="font-mono">{email}</strong>. The link expires in 15 minutes.
            </p>
            <button
              type="button"
              onClick={() => {
                setSent(false);
                setEmail("");
              }}
              className="mt-4 text-xs font-mono text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
            >
              Try a different email
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <label className="label block mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="w-full px-3 py-2 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm focus:outline-none focus:border-[var(--color-accent)] mb-4"
              required
            />
            {error && (
              <div className="px-3 py-2 bg-[var(--color-error-bg)] border border-red-200 text-red-700 font-mono text-sm mb-4">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={loading || !email.trim()}
              className="w-full px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium disabled:opacity-50"
            >
              {loading ? "Sending..." : "Send Magic Link"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
