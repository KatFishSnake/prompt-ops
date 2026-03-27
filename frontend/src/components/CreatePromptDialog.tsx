"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function CreatePromptDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (id: string) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setSaving(true);
    setError("");
    try {
      const prompt = await api.createPrompt({ name: name.trim(), description });
      onCreated(prompt.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create prompt");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] w-[440px] p-6">
        <h2 className="font-mono text-lg font-semibold mb-4">Create Prompt</h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="label block mb-2">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. customer-support-agent"
              className="w-full px-3 py-2 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm focus:outline-none focus:border-[var(--color-accent)]"
              autoFocus
            />
          </div>

          <div className="mb-4">
            <label className="label block mb-2">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What this prompt does..."
              className="w-full px-3 py-2 border border-[var(--color-border)] bg-[var(--color-bg)] text-sm focus:outline-none focus:border-[var(--color-accent)]"
            />
          </div>

          {error && (
            <div className="mb-4 px-3 py-2 bg-[var(--color-error-bg)] border border-red-200 text-red-700 text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-[var(--color-border)] font-mono text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !name.trim()}
              className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium disabled:opacity-50"
            >
              {saving ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
