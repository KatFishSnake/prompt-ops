"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  {
    section: "MANAGE",
    items: [
      { label: "Prompts", href: "/" },
      { label: "Traces", href: "/traces" },
    ],
  },
  { section: "TEST", items: [{ label: "Replays", href: "/replay" }] },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="w-[200px] min-h-screen border-r border-[var(--color-border)] bg-[var(--color-sidebar)] flex flex-col p-4 shrink-0">
      <Link
        href="/"
        className="font-mono text-lg font-bold tracking-tight mb-8 text-[var(--color-text-primary)]"
      >
        PromptOps
      </Link>

      <div className="flex-1 flex flex-col">
      {NAV_ITEMS.map((section) => (
        <div key={section.section} className="mb-6">
          <div className="label mb-3">{section.section}</div>
          {section.items.map((item) => {
            const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`block py-2 px-3 mb-1 font-mono text-sm transition-colors duration-75 ${
                  isActive
                    ? "bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-semibold"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      ))}
      <div className="mt-auto pt-4 text-[10px] font-mono text-[var(--color-text-muted)]">
        v{process.env.NEXT_PUBLIC_APP_VERSION}
      </div>
      </div>
    </nav>
  );
}
