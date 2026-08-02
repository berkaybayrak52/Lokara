import type { HTMLAttributes, ReactNode } from 'react';

import { cn } from './lib/cn';

/**
 * Status feedback per docs/05: a tint surface + icon + text label — never
 * colour alone (BFSG). Success reuses the brand green by design; what makes it
 * feedback rather than an action is the FORM (tinted, iconed, labeled).
 */

type StatusKind = 'success' | 'warning' | 'danger';

const surfaceByKind: Record<StatusKind, string> = {
  success: 'bg-success-tint text-success',
  warning: 'bg-warning-tint text-warning',
  danger: 'bg-danger-tint text-danger',
};

const labelColorByKind: Record<StatusKind, string> = {
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
};

// Filled 20px glyphs — distinct SHAPES per status, so the kind is readable
// without colour: circle-check / triangle-exclamation / circle-cross.
const iconByKind: Record<StatusKind, ReactNode> = {
  success: (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className="size-5 shrink-0">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.86-9.94a.75.75 0 1 0-1.22-.87l-2.96 4.14-1.4-1.4a.75.75 0 1 0-1.06 1.06l2.03 2.03a.75.75 0 0 0 1.14-.09l3.47-4.87Z"
      />
    </svg>
  ),
  warning: (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className="size-5 shrink-0">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M8.68 3.03c.6-1.04 2.04-1.04 2.64 0l6.7 11.6c.58 1-.16 2.24-1.32 2.24H3.3c-1.16 0-1.9-1.25-1.32-2.25l6.7-11.6ZM10 7a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 7Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
      />
    </svg>
  ),
  danger: (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className="size-5 shrink-0">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM7.28 7.28a.75.75 0 0 1 1.06 0L10 8.94l1.66-1.66a.75.75 0 1 1 1.06 1.06L11.06 10l1.66 1.66a.75.75 0 1 1-1.06 1.06L10 11.06l-1.66 1.66a.75.75 0 0 1-1.06-1.06L8.94 10 7.28 8.34a.75.75 0 0 1 0-1.06Z"
      />
    </svg>
  ),
};

export interface StatusNoteProps extends HTMLAttributes<HTMLDivElement> {
  kind: StatusKind;
  /** Short bold lead-in (the label that names the status). */
  label: string;
}

export function StatusNote({ kind, label, className, children, ...props }: StatusNoteProps) {
  return (
    <div
      role={kind === 'danger' ? 'alert' : 'status'}
      className={cn('flex items-start gap-3 rounded-lg p-4 font-sans', surfaceByKind[kind], className)}
      {...props}
    >
      {iconByKind[kind]}
      <p className="text-sm leading-5 text-ink">
        <span className={cn('font-semibold', labelColorByKind[kind])}>{label}</span>
        {children ? <> {children}</> : null}
      </p>
    </div>
  );
}
