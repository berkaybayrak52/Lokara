import type { InputHTMLAttributes } from 'react';

import { cn } from './lib/cn';

/**
 * shadcn-style Input on the brand tokens. Explicit visible label required
 * (use <Label htmlFor>) — placeholder is never the label (docs/05 "7-to-70").
 * `aria-invalid` switches the border to the danger token; the consuming form
 * pairs it with a text error (BFSG: never colour alone).
 */
export function Input({ className, type, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      type={type}
      className={cn(
        'h-10 w-full rounded-lg border border-slate bg-white px-3 py-2 font-sans text-sm text-ink',
        'placeholder:text-slate/70',
        'focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-danger aria-invalid:focus-visible:outline-danger',
        className,
      )}
      {...props}
    />
  );
}
