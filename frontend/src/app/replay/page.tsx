"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type ReplayJob } from "@/lib/api";

export default function ReplaysPage() {
  const [replays, setReplays] = useState<ReplayJob[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    api
      .listReplays()
      .then(setReplays)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6">
      <h1 className="font-mono text-[28px] font-semibold mb-6">Replays</h1>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 bg-[var(--color-border-light)] animate-pulse" />
          ))}
        </div>
      ) : replays.length === 0 ? (
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center">
          <p className="font-mono text-lg mb-2">No replays run yet</p>
          <p className="text-[var(--color-text-muted)] text-sm">
            Select a prompt and run "Replay vs Active" to compare versions.
          </p>
        </div>
      ) : (
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="label text-left py-3 px-4">Replay</th>
                <th className="label text-left py-3 px-4">Status</th>
                <th className="label text-left py-3 px-4">Results</th>
                <th className="label text-left py-3 px-4">Traces</th>
                <th className="label text-left py-3 px-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {replays.map((r) => (
                <tr
                  key={r.id}
                  className="border-b border-[var(--color-border-light)] hover:bg-[var(--color-bg)] cursor-pointer transition-colors duration-75"
                  onClick={() => router.push(`/replay/${r.id}`)}
                >
                  <td className="py-3 px-4 font-mono text-sm">{r.id.slice(0, 8)}...</td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-block px-2 py-0.5 text-xs font-mono font-medium border ${
                        r.status === "complete"
                          ? "bg-[var(--color-success-bg)] border-emerald-200 text-emerald-700"
                          : r.status === "running"
                            ? "bg-[var(--color-info-bg)] border-blue-200 text-blue-700"
                            : r.status === "failed"
                              ? "bg-[var(--color-error-bg)] border-red-200 text-red-700"
                              : "bg-[var(--color-warning-bg)] border-amber-200 text-amber-700"
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono text-xs">
                    {r.status === "complete" ? (
                      <>
                        <span className="text-emerald-600">{r.improved}↑</span>{" "}
                        <span className="text-[var(--color-text-muted)]">{r.unchanged}=</span>{" "}
                        <span className="text-red-500">{r.regressed}↓</span>
                      </>
                    ) : (
                      <span className="text-[var(--color-text-muted)]">—</span>
                    )}
                  </td>
                  <td className="py-3 px-4 font-mono text-sm">{r.trace_count}</td>
                  <td className="py-3 px-4 font-mono text-xs text-[var(--color-text-muted)]">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
