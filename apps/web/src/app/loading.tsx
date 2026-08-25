import Image from 'next/image';

export default function LoadingPage() {
  return (
    <main
      className="mx-auto flex min-h-dvh w-full max-w-xl flex-col justify-center px-6 py-16"
      role="status"
      aria-label="Seite wird geladen"
      aria-busy="true"
    >
      <Image src="/lokara-logo.png" alt="Lokara" width={132} height={36} priority />
      <div aria-hidden="true" className="mt-10 space-y-4">
        <div className="h-8 w-2/3 animate-pulse rounded-lg bg-mint motion-reduce:animate-none" />
        <div className="h-4 w-full animate-pulse rounded bg-mint/70 motion-reduce:animate-none" />
        <div className="h-4 w-4/5 animate-pulse rounded bg-mint/70 motion-reduce:animate-none" />
      </div>
      <span className="sr-only">Seite wird geladen …</span>
    </main>
  );
}
