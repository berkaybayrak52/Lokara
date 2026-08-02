'use client';

import { Input, Label } from '@lokara/ui';
import type { InputHTMLAttributes } from 'react';
import type { FieldError, UseFormRegisterReturn } from 'react-hook-form';

/** Label + input + text error in one accessible block: the error is tied via
 * aria-describedby and never signalled by colour alone (BFSG). */
export function FormField({
  id,
  label,
  hint,
  error,
  registration,
  ...inputProps
}: {
  id: string;
  label: string;
  hint?: string;
  error: FieldError | undefined;
  registration: UseFormRegisterReturn;
} & InputHTMLAttributes<HTMLInputElement>) {
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : hint ? hintId : undefined}
        {...inputProps}
        {...registration}
      />
      {error ? (
        <p id={errorId} className="text-sm font-medium text-danger">
          {error.message}
        </p>
      ) : hint ? (
        <p id={hintId} className="text-sm text-slate">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
