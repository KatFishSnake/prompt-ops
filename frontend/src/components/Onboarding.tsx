"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type PromptListItem } from "@/lib/api";

export function Onboarding() {
  const [show, setShow] = useState(false);
  const [step, setStep] = useState(0);
  const [seedPromptId, setSeedPromptId] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const onboarded = localStorage.getItem("promptops-onboarded");
    if (!onboarded) {
      setShow(true);
      api.listPrompts().then((prompts: PromptListItem[]) => {
        if (prompts.length > 0) setSeedPromptId(prompts[0].id);
      }).catch(() => {});
    }
  }, []);

  if (!show) return null;

  const dismiss = () => {
    localStorage.setItem("promptops-onboarded", "true");
    setShow(false);
  };

  const steps = [
    {
      title: "Welcome to PromptOps.",
      body: "Manage, test, and deploy AI prompts with confidence. Your workspace comes with demo prompts to get started.",
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
      title: "Generate test scenarios with AI.",
      body: "Describe your use case, and we'll generate diverse test scenarios automatically. Run them to create real traces with actual LLM responses.",
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
              Try It →
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
      title: "Edit a prompt and replay against real traces.",
      body: "Change your prompt, click Replay vs Active, and instantly see which responses improved, stayed the same, or regressed. Side-by-side diffs with judge scores.",
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
              Open a Prompt →
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
      title: "Here's what you can do.",
      body: "Your workspace is ready. Explore the demo prompts, generate scenarios, run replays, or connect your own app via the Integration panel.",
      actions: (
        <div className="flex flex-col gap-3">
          {seedPromptId && (
            <button
              type="button"
              onClick={() => {
                dismiss();
                router.push(`/prompts/${seedPromptId}`);
              }}
              className="w-full px-4 py-2 bg-[var(--color-text-primary)] text-white font-mono text-sm font-medium"
            >
              Open Demo Prompt →
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              dismiss();
              router.push("/traces");
            }}
            className="w-full px-4 py-2 border border-[var(--color-border)] font-mono text-sm"
          >
            Browse Traces →
          </button>
          <button
            type="button"
            onClick={dismiss}
            className="w-full px-4 py-2 text-[var(--color-text-muted)] font-mono text-sm hover:text-[var(--color-text-primary)]"
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
