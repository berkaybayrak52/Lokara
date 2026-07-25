import type { LabelHTMLAttributes } from 'react';

import { cn } from './lib/cn';

/** Always-visible field label (docs/05: reduction never costs a clear label). */
export function Label({ className, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn('block font-sans text-sm font-medium text-ink', className)}
      {...props}
    />
  );
}
