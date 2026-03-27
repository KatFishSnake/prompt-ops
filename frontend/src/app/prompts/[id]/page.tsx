"use client";

import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";
import { DiffView } from "@/components/DiffView";
import { IntegrationPanel } from "@/components/IntegrationPanel";
import { Playground } from "@/components/Playground";
import { api, type Prompt, type PromptVersion } from "@/lib/api";

export default function PromptDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [editModel, setEditModel] = useState("gpt-4o-mini");
  const [editTemp, setEditTemp] = useState("0.7");
  const [editMaxTokens, setEditMaxTokens] = useState("1024");
  const [saving, setSaving] = useState(false);
  const [promoting, setPromoting] = useState(false);
  const [showPromoteConfirm, setShowPromoteConfirm] = useState(false);
  const [replayLoading, setReplayLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const router = useRouter();

  useEffect(() => {
    api.getPrompt(id).then((p) => {
      setPrompt(p);
      const active = p.versions.find((v) => v.is_active) || p.versions[0];
      if (active) selectVersion(active);
    });
  }, [id]);

  const selectVersion = (v: PromptVersion) => {
    setActiveTab(v.id);
    setEditContent(v.content);
    const mc = v.model_config_json || {};
    setEditModel((mc.model as string) || "gpt-4o-mini");
    setEditTemp(String(mc.temperature ?? 0.7));
    setEditMaxTokens(String(mc.max_tokens ?? 1024));
  };

  const currentVersion = prompt?.versions.find((v) => v.id === activeTab);
  const activeVersion = prompt?.versions.find((v) => v.is_active);

  const extractVars = (content: string) => {
    const matches = content.match(/\{\{(\w+)\}\}/g);
    if (!matches) return [];
    return [...new Set(matches.map((m) => m.replace(/[{}]/g, "")))];
  };

  const handleSaveNew = async () => {
    if (!prompt) return;
    setSaving(true);
    try {
      const version = await api.createVersion(prompt.id, {
        content: editContent,
        model_config: {
          model: editModel,
          temperature: parseFloat(editTemp),
          max_tokens: parseInt(editMaxTokens),
        },
      });
      const updated = await api.getPrompt(prompt.id);
      setPrompt(updated);
      selectVersion(version);
      showToast("Version saved", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to save", "error");
    } finally {
      setSaving(false);
    }
  };

  const handlePromote = async () => {
    if (!prompt || !currentVersion) return;
    setPromoting(true);
    try {
      await api.promote(prompt.id, currentVersion.id);
      const updated = await api.getPrompt(prompt.id);
      setPrompt(updated);
      setShowPromoteConfirm(false);
      showToast(`v${currentVersion.version_number} is now active`, "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to promote", "error");
    } finally {
      setPromoting(false);
    }
  };

  const handleReplay = async () => {
    if (!prompt || !activeVersion || !currentVersion) return;
    setReplayLoading(true);
    try {
      const job = await api.startReplay({
        prompt_id: prompt.id,
        source_version_id: activeVersion.id,
        target_version_id: currentVersion.id,
      });
      router.push(`/replay/${job.id}`);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to start replay", "error");
      setReplayLoading(false);
    }
  };

  const showToast = (message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  if (!prompt) {
    return (
      <div className="p-6">
        <div className="h-8 w-64 bg-[var(--color-border-light)] animate-pulse mb-6" />
        <div className="h-64 bg-[var(--color-border-light)] animate-pulse" />
      </div>
    );
  }

  const vars = extractVars(editContent);
  const showDiff = currentVersion && activeVersion && currentVersion.id !== activeVersion.id;

  return (
    <div className="p-6">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 border font-mono text-sm ${
            toast.type === "success"
              ? "bg-[var(--color-success-bg)] border-emerald-200 text-emerald-700"
              : "bg-[var(--color-error-bg)] border-red-200 text-red-700"
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* Promote confirm dialog */}
      {showPromoteConfirm && currentVersion && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] w-[440px] p-6">
            <h2 className="font-mono text-lg font-semibold mb-3">Promote Version</h2>
            <p className="text-sm text-[var(--color-text-muted)] mb-6">
              Promote v{currentVersion.version_number} to active? This replaces{" "}
              {activeVersion ? `v${activeVersion.version_number}` : "the current version"} for all
              consumers of this prompt.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setShowPromoteConfirm(false)}
                className="px-4 py-2 border border-[var(--color-border)] font-mono text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePromote}
                disabled={promoting}
                className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium disabled:opacity-50"
              >
                {promoting ? "Promoting..." : "Promote"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <h1 className="font-mono text-[28px] font-semibold">{prompt.name}</h1>
        {prompt.description && (
          <p className="text-sm text-[var(--color-text-muted)] mt-1">{prompt.description}</p>
        )}
      </div>

      {/* Version tabs */}
      <div className="flex items-center gap-1 mb-6 border-b border-[var(--color-border)] overflow-x-auto">
        {prompt.versions.map((v) => (
          <button
            type="button"
            key={v.id}
            onClick={() => selectVersion(v)}
            className={`px-4 py-2 font-mono text-sm whitespace-nowrap border-b-2 transition-colors duration-75 ${
              v.id === activeTab
                ? "border-[var(--color-accent)] text-[var(--color-accent)] font-medium"
                : "border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            v{v.version_number}
            {v.is_active && (
              <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-[var(--color-success-bg)] text-emerald-700 border border-emerald-200 font-semibold">
                ACTIVE
              </span>
            )}
          </button>
        ))}
        <button
          type="button"
          onClick={handleSaveNew}
          className="px-4 py-2 font-mono text-sm text-[var(--color-text-muted)] hover:text-[var(--color-accent)] border-b-2 border-transparent"
        >
          + New Version
        </button>
      </div>

      {/* Prompt Diff (between current tab and active version) */}
      {showDiff && activeVersion && (
        <div className="mb-4 border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <div className="label mb-3">Template Changes</div>
          <DiffView
            original={activeVersion.content}
            replayed={editContent}
            sourceLabel={`v${activeVersion.version_number} (active)`}
            targetLabel={`v${currentVersion.version_number} (viewing)`}
          />
        </div>
      )}

      {/* Editor */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)]">
        <div className="p-4">
          <label className="label block mb-2">Prompt Template</label>
          <textarea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            rows={12}
            className="w-full px-4 py-3 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm leading-relaxed resize-y focus:outline-none focus:border-[var(--color-accent)]"
            spellCheck={false}
            placeholder={"Write your prompt template here.\n\nUse {{variable_name}} to insert dynamic values at runtime.\nExample: \"You are a helpful assistant for {{product_name}}.\"\n\nVariables are automatically detected and shown below.\nThey'll appear as inputs in the Playground and as template_vars in the API."}
          />

          {/* Detected variables */}
          {vars.length > 0 && (
            <div className="mt-3">
              <span className="label">Detected Variables: </span>
              {vars.map((v) => (
                <span
                  key={v}
                  className="inline-block ml-2 px-2 py-0.5 bg-[var(--color-info-bg)] border border-blue-200 text-blue-700 font-mono text-xs"
                >
                  {`{{${v}}}`}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Model config */}
        <div className="border-t border-[var(--color-border)] p-4">
          <label className="label block mb-3">Model Config</label>
          <div className="flex gap-4 items-center">
            <div>
              <label className="text-xs text-[var(--color-text-muted)] block mb-1">Model</label>
              <select
                value={editModel}
                onChange={(e) => setEditModel(e.target.value)}
                className="px-3 py-2 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm"
              >
                <option value="gpt-4o-mini">gpt-4o-mini</option>
                <option value="gpt-4o">gpt-4o</option>
                <option value="gpt-4-turbo">gpt-4-turbo</option>
                <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[var(--color-text-muted)] block mb-1">
                Temperature
              </label>
              <input
                type="number"
                value={editTemp}
                onChange={(e) => setEditTemp(e.target.value)}
                min="0"
                max="2"
                step="0.1"
                className="w-20 px-3 py-2 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-[var(--color-text-muted)] block mb-1">
                Max Tokens
              </label>
              <input
                type="number"
                value={editMaxTokens}
                onChange={(e) => setEditMaxTokens(e.target.value)}
                className="w-24 px-3 py-2 border border-[var(--color-border)] bg-[var(--color-bg)] font-mono text-sm"
              />
            </div>
          </div>
          <div className="mt-3 px-3 py-2 bg-[var(--color-info-bg)] border border-blue-200 text-xs text-[var(--color-text-muted)]">
            <span className="font-mono font-medium text-blue-700">Tip:</span>{" "}
            <span className="font-mono text-blue-700">Temperature</span> controls randomness — use 0-0.3 for factual/deterministic tasks, 0.7-1.0 for creative writing.{" "}
            <span className="font-mono text-blue-700">Max Tokens</span> caps the response length — 256 for short answers, 1024+ for long-form content.
          </div>
        </div>

        {/* Actions */}
        <div className="border-t border-[var(--color-border)] p-4 flex gap-3">
          <button
            type="button"
            onClick={handleSaveNew}
            disabled={saving}
            className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium disabled:opacity-50"
          >
            {saving ? "Saving..." : `Save as v${(prompt.versions.length || 0) + 1}`}
          </button>

          {currentVersion && !currentVersion.is_active && activeVersion && (
            <button
              type="button"
              onClick={handleReplay}
              disabled={replayLoading}
              className="px-4 py-2 bg-[var(--color-accent)] text-white font-mono text-sm font-medium disabled:opacity-50"
            >
              {replayLoading ? "Starting..." : "▶ Replay vs Active"}
            </button>
          )}

          {currentVersion && !currentVersion.is_active && (
            <button
              type="button"
              onClick={() => setShowPromoteConfirm(true)}
              className="px-4 py-2 border border-emerald-300 text-emerald-700 font-mono text-sm font-medium hover:bg-[var(--color-success-bg)]"
            >
              ↑ Promote to Active
            </button>
          )}
        </div>
      </div>

      {/* Playground */}
      <Playground
        promptId={prompt.id}
        content={editContent}
        variables={vars}
        modelConfig={{
          model: editModel,
          temperature: parseFloat(editTemp),
          max_tokens: parseInt(editMaxTokens),
        }}
      />

      {/* Integration Panel */}
      <IntegrationPanel promptName={prompt.name} />
    </div>
  );
}
