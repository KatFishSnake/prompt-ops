"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { CreatePromptDialog } from "@/components/CreatePromptDialog";
import { Onboarding } from "@/components/Onboarding";
import { api, type PromptListItem } from "@/lib/api";

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const router = useRouter();

  useEffect(() => {
    api
      .listPrompts()
      .then(setPrompts)
      .finally(() => setLoading(false));
  }, []);

  const handleCreated = (id: string) => {
    setShowCreate(false);
    router.push(`/prompts/${id}`);
  };

  return (
    <div className="p-6">
      <Onboarding />

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-mono text-[28px] font-semibold">Prompts</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">Versioned templates for your AI models. Create, edit, and promote prompts to production.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium hover:opacity-90 transition-opacity"
        >
          Create Prompt
        </button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-[var(--color-border-light)] animate-pulse" />
          ))}
        </div>
      ) : prompts.length === 0 ? (
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center">
          <p className="font-mono text-lg mb-2">No prompts yet</p>
          <p className="text-[var(--color-text-muted)] text-sm mb-4">
            Create your first prompt to get started. Prompts are versioned templates that you can
            test against real traffic.
          </p>
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium"
          >
            Create Prompt
          </button>
        </div>
      ) : (
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="label text-left py-3 px-4">Name</th>
                <th className="label text-left py-3 px-4">Active Version</th>
                <th className="label text-left py-3 px-4">Versions</th>
                <th className="label text-left py-3 px-4">Last Replay</th>
                <th className="label text-left py-3 px-4">Updated</th>
              </tr>
            </thead>
            <tbody>
              {prompts.map((p) => (
                <tr
                  key={p.id}
                  className="border-b border-[var(--color-border-light)] hover:bg-[var(--color-bg)] cursor-pointer transition-colors duration-75"
                  onClick={() => router.push(`/prompts/${p.id}`)}
                >
                  <td className="py-3 px-4">
                    <div className="font-mono text-sm font-medium">{p.name}</div>
                    <div className="text-xs text-[var(--color-text-muted)] mt-0.5 truncate max-w-[300px]">
                      {p.description}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    {p.active_version ? (
                      <span className="inline-block px-2 py-0.5 text-xs font-mono font-medium bg-[var(--color-success-bg)] text-emerald-700 border border-emerald-200">
                        v{p.active_version}
                      </span>
                    ) : (
                      <span className="text-xs text-[var(--color-text-muted)]">none</span>
                    )}
                  </td>
                  <td className="py-3 px-4 font-mono text-sm">{p.version_count}</td>
                  <td className="py-3 px-4">
                    {p.latest_replay ? (
                      <Link
                        href={`/replay/${p.latest_replay.job_id}`}
                        className="font-mono text-xs hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <span className="text-emerald-600">{p.latest_replay.improved}↑</span>{" "}
                        <span className="text-[var(--color-text-muted)]">
                          {p.latest_replay.unchanged}=
                        </span>{" "}
                        <span className="text-red-500">{p.latest_replay.regressed}↓</span>
                      </Link>
                    ) : (
                      <span className="text-xs text-[var(--color-text-muted)]">No replays</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-xs text-[var(--color-text-muted)] font-mono">
                    {new Date(p.updated_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreatePromptDialog onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}
    </div>
  );
}
