"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type PromptListItem } from "@/lib/api";

export function Onboarding() {
  const [show, setShow] = useState(false);
  const [step, setStep] = useState(0);
  const [seedReplayId, setSeedReplayId] = useState<string | null>(null);
  const [seedPromptId, setSeedPromptId] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const onboarded = localStorage.getItem("promptops-onboarded");
    if (!onboarded) {
      setShow(true);
      api.listReplays().then((replays) => {
        const completed = replays.find((r) => r.status === "complete");
        if (completed) setSeedReplayId(completed.id);
      });
      api.listPrompts().then((prompts: PromptListItem[]) => {
        if (prompts.length > 0) setSeedPromptId(prompts[0].id);
      });
    }
  }, []);

  if (!show) return null;

  const dismiss = () => {
    localStorage.setItem("promptops-onboarded", "true");
    setShow(false);
  };

  const steps = [
    {
      title: "PromptOps manages your AI prompts in production.",
      body: "Version prompts, test changes against real traffic, deploy with confidence.",
      actions: (
        <button
          type="button"
          onClick={() => setStep(1)}
          className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium"
        >
          Next
        </button>
      ),
    },
    {
      title: "We replayed 20 real traces against a new prompt. See what changed.",
      body: "Side-by-side diffs show exactly how each response changed. Judge scores tell you if it got better or worse.",
      actions: (
        <div className="flex gap-3">
          {seedReplayId && (
            <button
              type="button"
              onClick={() => {
                dismiss();
                router.push(`/replay/${seedReplayId}`);
              }}
              className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium"
            >
              See Replay Results →
            </button>
          )}
          <button
            type="button"
            onClick={() => setStep(2)}
            className="px-4 py-2 border border-[var(--color-border)] font-mono text-sm"
          >
            Next
          </button>
        </div>
      ),
    },
    {
      title: "Try editing a prompt yourself.",
      body: "Open the playground to test your prompt live. See the LLM response in real time.",
      actions: (
        <div className="flex gap-3">
          {seedPromptId && (
            <button
              type="button"
              onClick={() => {
                dismiss();
                router.push(`/prompts/${seedPromptId}#playground`);
              }}
              className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium"
            >
              Open Playground →
            </button>
          )}
          <button
            type="button"
            onClick={() => setStep(3)}
            className="px-4 py-2 border border-[var(--color-border)] font-mono text-sm"
          >
            Next
          </button>
        </div>
      ),
    },
    {
      title: "Connect your app in 2 lines of code.",
      body: "Fetch the active prompt at runtime, send traces after each LLM call. The Integration panel on each prompt page has ready-to-copy code.",
      actions: (
        <div className="flex gap-3">
          {seedPromptId && (
            <button
              type="button"
              onClick={() => {
                dismiss();
                router.push(`/prompts/${seedPromptId}`);
              }}
              className="px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium"
            >
              See Integration Guide →
            </button>
          )}
          <button
            type="button"
            onClick={dismiss}
            className="px-4 py-2 border border-[var(--color-border)] font-mono text-sm"
          >
            Explore on my own
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] w-[480px] p-8">
        <div className="flex justify-between items-center mb-6">
          <span className="label">
            Step {step + 1}/{steps.length}
          </span>
          <button
            type="button"
            onClick={dismiss}
            className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] font-mono"
          >
            Skip
          </button>
        </div>

        <h2 className="font-mono text-xl font-semibold mb-3">{steps[step].title}</h2>
        {steps[step].body && (
          <p className="text-sm text-[var(--color-text-muted)] mb-8">{steps[step].body}</p>
        )}

        {steps[step].actions}
      </div>
    </div>
  );
}
