'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { Button, Input, Label, StatusNote } from '@lokara/ui';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

const LoginSchema = z.object({
  email: z.string().trim().email('Bitte geben Sie eine gültige E-Mail-Adresse ein.'),
});

type LoginInput = z.infer<typeof LoginSchema>;

export function LoginForm({ initialError = false }: { initialError?: boolean }) {
  const [sent, setSent] = useState(false);
  const [requestError, setRequestError] = useState(initialError);
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
  } = useForm<LoginInput>({
    defaultValues: { email: '' },
    resolver: zodResolver(LoginSchema),
  });

  const submit = handleSubmit(async (input) => {
    setRequestError(false);
    const response = await fetch('/api/auth/magic-link', {
      body: JSON.stringify(input),
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      method: 'POST',
    }).catch(() => null);

    if (!response?.ok) {
      setRequestError(true);
      return;
    }
    setSent(true);
  });

  if (sent) {
    return (
      <StatusNote kind="success" label="E-Mail wurde angefordert.">
        Wenn diese Adresse eingeladen wurde, erhalten Sie gleich einen sicheren Anmeldelink.
      </StatusNote>
    );
  }

  return (
    <form className="space-y-5" onSubmit={submit} noValidate>
      <div className="space-y-2">
        <Label htmlFor="email">E-Mail-Adresse</Label>
        <Input
          id="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          autoFocus
          aria-invalid={errors.email ? true : undefined}
          aria-describedby={errors.email ? 'email-error' : undefined}
          {...register('email')}
        />
        {errors.email ? (
          <p id="email-error" className="text-sm text-danger">
            {errors.email.message}
          </p>
        ) : null}
      </div>

      {requestError ? (
        <StatusNote kind="danger" label="Anmeldung nicht möglich.">
          Der Link ist ungültig oder der Anmeldedienst ist gerade nicht erreichbar. Bitte versuchen
          Sie es erneut.
        </StatusNote>
      ) : null}

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? 'Link wird angefordert …' : 'Anmeldelink anfordern'}
      </Button>
    </form>
  );
}
