import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { Manrope, Montserrat } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

// docs/05: Montserrat = display (headlines, big numbers), Manrope = text.
const montserrat = Montserrat({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-montserrat',
  display: 'swap',
});
const manrope = Manrope({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-manrope',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Lokara',
  description: 'Rechtskonforme Nebenkosten- und Betriebskostenabrechnung.',
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
