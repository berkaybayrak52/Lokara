import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@lokara/ui';
import Image from 'next/image';

import { LoginForm } from '@/features/auth/login-form';

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center px-6 py-16">
      <Image
        src="/lokara-logo.png"
        alt="Lokara"
        width={147}
        height={40}
        priority
        className="mb-8 h-10 w-auto self-start"
      />
      <Card>
        <CardHeader>
          <CardTitle className="font-display text-2xl">Bei Lokara anmelden</CardTitle>
          <CardDescription>
            Geben Sie die E-Mail-Adresse ein, an die Ihre persönliche Einladung gesendet wurde.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <LoginForm initialError={error !== undefined} />
          <p className="text-sm leading-6 text-slate">
            Lokara ist derzeit nur auf Einladung zugänglich. Es gibt keine öffentliche
            Registrierung.
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
