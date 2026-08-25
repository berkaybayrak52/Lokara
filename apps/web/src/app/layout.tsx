import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';
import { manrope, montserrat } from './fonts';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'Lokara',
  description: 'Vermieten leicht gemacht — Verwaltung über den ganzen Lebenszyklus.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="de" className={`${montserrat.variable} ${manrope.variable}`}>
      <body className="bg-paper font-sans text-ink antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
