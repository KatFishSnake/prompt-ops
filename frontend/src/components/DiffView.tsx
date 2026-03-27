"use client";

import DiffMatchPatch from "diff-match-patch";
import { useMemo } from "react";

const dmp = new DiffMatchPatch();

export function DiffView({
  original,
  replayed,
  sourceLabel,
  targetLabel,
}: {
  original: string;
  replayed: string;
  sourceLabel: string;
  targetLabel: string;
}) {
  const diffs = useMemo(() => {
    const d = dmp.diff_main(original, replayed);
    dmp.diff_cleanupSemantic(d);
    return d;
  }, [original, replayed]);

  const renderDiff = (side: "original" | "replayed") => {
    return diffs.map(([op, text], i) => {
      if (op === 0) {
        return <span key={i}>{text}</span>;
      }
      if (op === -1 && side === "original") {
        return (
          <span key={i} className="bg-red-100 text-red-800 line-through">
            {text}
          </span>
        );
      }
      if (op === 1 && side === "replayed") {
        return (
          <span key={i} className="bg-emerald-100 text-emerald-800">
            {text}
          </span>
        );
      }
      return null;
    });
  };

  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <div className="label mb-2">{sourceLabel}</div>
        <div className="bg-[var(--color-bg)] border border-[var(--color-border)] p-3 text-sm whitespace-pre-wrap max-h-64 overflow-y-auto">
          {renderDiff("original")}
        </div>
      </div>
      <div>
        <div className="label mb-2">{targetLabel}</div>
        <div className="bg-[var(--color-bg)] border border-[var(--color-border)] p-3 text-sm whitespace-pre-wrap max-h-64 overflow-y-auto">
          {renderDiff("replayed")}
        </div>
      </div>
    </div>
  );
}
