import type { SelectHTMLAttributes } from 'react';

import { cn } from './lib/cn';

/**
 * Native `<select>` on the brand tokens. Native on purpose: it is keyboard- and
 * screen-reader-correct everywhere and uses the platform picker on mobile — a
 * custom listbox would owe all of that back (docs/05 a11y checklist). Swap for
 * a Radix Select only when multi-select or rich option content demands it.
 */
export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        'h-10 w-full appearance-none rounded-lg border border-slate bg-white px-3 py-2',
        'font-sans text-sm text-ink',
        // Chevron drawn as a background image so no wrapper element is needed;
        // encoded inline (no external asset) and in the Slate token colour.
        "bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 20 20%22 fill=%22%235c6a6b%22%3E%3Cpath fill-rule=%22evenodd%22 d=%22M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.17l3.71-3.94a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z%22 clip-rule=%22evenodd%22/%3E%3C/svg%3E')]",
        'bg-[length:1.25rem_1.25rem] bg-[position:right_0.5rem_center] bg-no-repeat pr-9',
        'focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-danger aria-invalid:focus-visible:outline-danger',
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}
