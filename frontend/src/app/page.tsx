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
  const [deleteTarget, setDeleteTarget] = useState<PromptListItem | null>(null);
  const [deleting, setDeleting] = useState(false);
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
                <th className="label text-right py-3 px-4" />
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
                  <td className="py-3 px-4 text-right">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(p);
                      }}
                      className="px-2 py-1 text-[10px] font-mono border border-red-200 text-red-500 hover:bg-[var(--color-error-bg)]"
                    >
                      Delete
                    </button>
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

      {deleteTarget && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] w-[440px] p-6">
            <h2 className="font-mono text-lg font-semibold mb-3">Delete Prompt</h2>
            <p className="text-sm text-[var(--color-text-muted)] mb-6">
              Delete <strong>{deleteTarget.name}</strong>? This will hide it from the list.
              Existing replays and traces will still be accessible.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 border border-[var(--color-border)] font-mono text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  setDeleting(true);
                  try {
                    await api.deletePrompt(deleteTarget.id);
                    setPrompts(prompts.filter((p) => p.id !== deleteTarget.id));
                    setDeleteTarget(null);
                  } catch (err) {
                    alert(err instanceof Error ? err.message : "Failed to delete");
                  } finally {
                    setDeleting(false);
                  }
                }}
                disabled={deleting}
                className="px-4 py-2 bg-red-500 text-white font-mono text-sm font-medium disabled:opacity-50"
              >
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
