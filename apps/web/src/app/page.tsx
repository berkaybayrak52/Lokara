import { BrandSection } from '@/features/demo/brand-section';
import { SummarySection } from '@/features/demo/summary-section';

/**
 * Demo page (migration Phase F): design tokens + shadcn-themed components
 * render, and live data flows web → api.ts interceptor (HttpOnly cookie,
 * 401 → refresh once → replay) → FastAPI → RLS-scoped Postgres.
 */
export default function Home() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <header className="mb-12">
        <p className="mb-2 font-sans text-sm font-semibold text-green">
          Lokara · Migration Phase F
        </p>
        <h1 className="font-display text-4xl font-bold">Räume mit klarer Struktur</h1>
        <p className="mt-3 max-w-prose text-slate">
          Diese Seite belegt das Fundament: Design-Tokens, Schriften (Montserrat für Headlines,
          Manrope für Text) und der Datenfluss Web-App → FastAPI → Datenbank durch den
          Auth-Interceptor.
        </p>
      </header>

      <BrandSection />
      <SummarySection />

      <footer className="mt-16 border-t border-mint pt-6 text-sm text-slate">
        Rechtskonform erstellt — keine Rechts- oder Steuerberatung.
      </footer>
    </main>
  );
}
