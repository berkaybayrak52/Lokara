import { BrandSection } from '@/features/demo/brand-section';

/** Public design-system reference without development or infrastructure copy. */
export default function Home() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <header className="mb-12">
        <p className="mb-2 font-sans text-sm font-semibold text-green">Lokara Designsystem</p>
        <h1 className="font-display text-4xl font-bold">Räume mit klarer Struktur</h1>
        <p className="mt-3 max-w-prose text-slate">
          Farben, Schriften und Oberflächen für eine ruhige, verständliche Verwaltung.
        </p>
      </header>

      <BrandSection />
      {/*
        The lifecycle-wide web disclaimer preserves the required "rechtskonform"
        and "keine Rechts- oder Steuerberatung" boundaries without framing
        Lokara as an accounting-only product.
      */}
      <footer className="mt-16 border-t border-mint pt-6 text-sm text-slate">
        Lokara unterstützt Vermieter bei der rechtskonformen Verwaltung ihrer Objekte und ersetzt
        keine Rechts- oder Steuerberatung.
      </footer>
    </main>
  );
}
