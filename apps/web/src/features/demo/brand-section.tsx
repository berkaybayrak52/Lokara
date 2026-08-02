'use client';

import { Button, Card, CardContent } from '@lokara/ui';
import { atom, useAtom } from 'jotai';

/**
 * Design-token showcase. Progressive disclosure (docs/05): the palette detail
 * hides behind "Mehr anzeigen" — UI state lives in a Jotai atom.
 */

const paletteExpandedAtom = atom(false);

const PALETTE = [
  { name: 'Petrol Ink', token: 'ink', className: 'bg-ink', hex: '#18212A' },
  { name: 'Lokara Grün', token: 'green', className: 'bg-green', hex: '#1A6558' },
  { name: 'Forest Deep', token: 'forest', className: 'bg-forest', hex: '#123F37' },
  { name: 'Mint Tint', token: 'mint', className: 'bg-mint', hex: '#E7EFEB' },
  { name: 'Slate', token: 'slate', className: 'bg-slate', hex: '#5C6A6B' },
  { name: 'Paper', token: 'paper', className: 'bg-paper', hex: '#FBFBFA' },
] as const;

export function BrandSection() {
  const [expanded, setExpanded] = useAtom(paletteExpandedAtom);
  const visible = expanded ? PALETTE : PALETTE.slice(0, 3);

  return (
    <>
      <section aria-labelledby="palette-heading" className="mb-12">
        <h2 id="palette-heading" className="mb-4 font-display text-2xl font-semibold">
          Farbpalette
        </h2>
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {visible.map((color) => (
            <li key={color.token} className="overflow-hidden rounded-lg border border-mint">
              <div className={`h-16 ${color.className}`} aria-hidden="true" />
              <div className="bg-white p-3">
                <p className="font-semibold">{color.name}</p>
                <p className="text-sm text-slate">
                  {color.token} · {color.hex}
                </p>
              </div>
            </li>
          ))}
        </ul>
        <Button
          variant="ghost"
          size="sm"
          className="mt-3"
          aria-expanded={expanded}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? 'Weniger anzeigen' : 'Mehr anzeigen'}
        </Button>
      </section>

      <section aria-labelledby="type-heading" className="mb-12">
        <h2 id="type-heading" className="mb-4 font-display text-2xl font-semibold">
          Typografie
        </h2>
        <Card className="bg-mint shadow-none">
          <CardContent className="p-6">
            <p className="font-display text-3xl font-bold">Montserrat — 1.200,00 €</p>
            <p className="mt-2 font-sans">
              Manrope trägt Fließtext, Labels und Tabellen — von der Visitenkarte bis zum
              Dashboard.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button>Abrechnung erstellen</Button>
              <Button variant="outline">Mehr anzeigen</Button>
            </div>
          </CardContent>
        </Card>
      </section>
    </>
  );
}
