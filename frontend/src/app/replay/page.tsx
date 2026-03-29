"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api, type ReplayJob } from "@/lib/api";

function groupByPromptName(replays: ReplayJob[]): Map<string, ReplayJob[]> {
  const groups = new Map<string, ReplayJob[]>();
  for (const r of replays) {
    const key = r.prompt_name?.trim() || "Unknown";
    const list = groups.get(key);
    if (list) {
      list.push(r);
    } else {
      groups.set(key, [r]);
    }
  }
  return groups;
}

function formatVersions(r: ReplayJob): string {
  const src =
    r.source_version_number != null ? `v${r.source_version_number}` : "?";
  const tgt =
    r.target_version_number != null ? `v${r.target_version_number}` : "?";
  return `${src} → ${tgt}`;
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "complete"
      ? "bg-[var(--color-success-bg)] border-emerald-200 text-emerald-700"
      : status === "running"
        ? "bg-[var(--color-info-bg)] border-blue-200 text-blue-700"
        : status === "failed"
          ? "bg-[var(--color-error-bg)] border-red-200 text-red-700"
          : "bg-[var(--color-warning-bg)] border-amber-200 text-amber-700";
  return (
    <span
      className={`inline-block px-2 py-0.5 text-xs font-mono font-medium border ${cls}`}
    >
      {status}
    </span>
  );
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className={`transition-transform duration-150 ${expanded ? "rotate-90" : ""}`}
    >
      <path
        d="M6 4l4 4-4 4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="square"
      />
    </svg>
  );
}

export default function ReplaysPage() {
  const [replays, setReplays] = useState<ReplayJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const router = useRouter();

  const groups = useMemo(() => groupByPromptName(replays), [replays]);

  useEffect(() => {
    api
      .listReplays()
      .then((data) => {
        setReplays(data);
        const allKeys = new Set<string>();
        for (const r of data) {
          allKeys.add(r.prompt_name?.trim() || "Unknown");
        }
        setExpandedGroups(allKeys);
      })
      .finally(() => setLoading(false));
  }, []);

  function toggleGroup(name: string) {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="font-mono text-[28px] font-semibold">Replays</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Side-by-side comparisons of prompt versions tested against real
          traffic.
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-14 bg-[var(--color-border-light)] animate-pulse"
            />
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
        <div className="space-y-3">
          {Array.from(groups.entries()).map(([promptName, groupReplays]) => {
            const expanded = expandedGroups.has(promptName);
            return (
              <div
                key={promptName}
                className="border border-[var(--color-border)] bg-[var(--color-surface)]"
              >
                {/* Group header */}
                <button
                  type="button"
                  onClick={() => toggleGroup(promptName)}
                  className="w-full flex items-center gap-3 py-3 px-4 hover:bg-[var(--color-bg)] transition-colors duration-75 text-left"
                >
                  <ChevronIcon expanded={expanded} />
                  <span className="font-mono text-sm font-bold">
                    {promptName}
                  </span>
                  <span className="ml-auto font-mono text-xs text-[var(--color-text-muted)] border border-[var(--color-border)] px-2 py-0.5">
                    {groupReplays.length}
                  </span>
                </button>

                {/* Group body */}
                {expanded && (
                  <div className="border-t border-[var(--color-border)]">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-[var(--color-border)]">
                          <th className="label text-left py-2.5 px-4">
                            Versions
                          </th>
                          <th className="label text-left py-2.5 px-4">
                            Status
                          </th>
                          <th className="label text-left py-2.5 px-4">
                            Results
                          </th>
                          <th className="label text-left py-2.5 px-4">
                            Traces
                          </th>
                          <th className="label text-left py-2.5 px-4">
                            Created
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {groupReplays.map((r) => (
                          <tr
                            key={r.id}
                            className="border-b border-[var(--color-border-light)] hover:bg-[var(--color-bg)] cursor-pointer transition-colors duration-75"
                            onClick={() => router.push(`/replay/${r.id}`)}
                          >
                            <td className="py-3 px-4 font-mono text-sm">
                              {formatVersions(r)}
                            </td>
                            <td className="py-3 px-4">
                              <StatusBadge status={r.status} />
                            </td>
                            <td className="py-3 px-4 font-mono text-xs">
                              {r.status === "complete" ? (
                                <>
                                  <span className="text-emerald-600">
                                    {r.improved}↑
                                  </span>{" "}
                                  <span className="text-[var(--color-text-muted)]">
                                    {r.unchanged}=
                                  </span>{" "}
                                  <span className="text-red-500">
                                    {r.regressed}↓
                                  </span>
                                </>
                              ) : (
                                <span className="text-[var(--color-text-muted)]">
                                  —
                                </span>
                              )}
                            </td>
                            <td className="py-3 px-4 font-mono text-sm">
                              {r.trace_count}
                            </td>
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
          })}
        </div>
      )}
    </div>
  );
}
