'use client';

import { useEffect, useRef, useState } from 'react';

/**
 * Rechte Reminder-/Wächter-Leiste als Glocken-Button (Pitch-Demo).
 *
 * Eingeklappt ist nur die Glocke oben rechts sichtbar (mit Badge für dringende
 * Fristen); ein Klick öffnet das Panel, Escape oder Klick außerhalb schließt es.
 *
 * HINWEIS: Das echte Reminder-/Wächter-System (Deadlines, Eichfrist, § 556, UVI,
 * Arrears über EIN Guard-Muster) ist laut Spec ein eigenes, späteres Modul und
 * hier NOCH NICHT implementiert. Diese Leiste zeigt bewusst als Demo
 * gekennzeichnete Beispiel-Fristen aus den bekannten Demo-Fakten. Keine Zahl ist
 * eine verbindliche Rechts-/Fristauskunft; nichts wird gespeichert oder verlinkt.
 */

type Severity = 'danger' | 'warning' | 'info';

interface Reminder {
  severity: Severity;
  tag: string;
  title: string;
  detail: string;
  when: string;
}

const REMINDERS: Reminder[] = [
  {
    severity: 'danger',
    tag: 'Überfällig',
    title: 'Eichfrist abgelaufen',
    detail: 'Kaltwasserzähler KWZ-C-441097, Musterstraße 12',
    when: 'seit 31.12.2025',
  },
  {
    severity: 'warning',
    tag: 'Bald fällig',
    title: 'Eichfrist läuft ab',
    detail: 'Hauptwärmezähler Hafenallee 27',
    when: '30.11.2026',
  },
  {
    severity: 'warning',
    tag: 'Bald fällig',
    title: 'Bank-Zustimmung läuft ab',
    detail: 'Mietkonto Hafenallee (PSD2/finAPI-Demo)',
    when: 'in 12 Tagen',
  },
  {
    severity: 'warning',
    tag: 'Zu prüfen',
    title: '2 Zahlungen offen',
    detail: 'Eva König · Absenderwechsel, Maria Santos · Überzahlung',
    when: 'laufender Monat',
  },
  {
    severity: 'info',
    tag: 'Hinweis',
    title: 'Abrechnungsfrist 2025',
    detail: 'Betriebskostenabrechnung an Mieter (§ 556 Abs. 3 BGB)',
    when: 'bis 31.12.2026',
  },
];

const SEVERITY_DOT: Record<Severity, string> = {
  danger: 'bg-danger',
  warning: 'bg-warning',
  info: 'bg-green',
};
const SEVERITY_TEXT: Record<Severity, string> = {
  danger: 'text-danger',
  warning: 'text-warning',
  info: 'text-forest',
};

function BellIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  );
}

export function ReminderSidebar() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const urgentCount = REMINDERS.filter((reminder) => reminder.severity !== 'info').length;
  const hasDanger = REMINDERS.some((reminder) => reminder.severity === 'danger');

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    const onPointerDown = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('mousedown', onPointerDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('mousedown', onPointerDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="fixed top-4 right-4 z-40">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={`Fristen & Erinnerungen${urgentCount > 0 ? `, ${urgentCount} offen` : ''}`}
        title="Fristen & Erinnerungen"
        className="relative flex h-11 w-11 items-center justify-center rounded-full border border-mint bg-white text-ink shadow-sm transition-colors hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        <BellIcon />
        {urgentCount > 0 ? (
          <span
            aria-hidden="true"
            className={`absolute -top-0.5 -right-0.5 flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[11px] font-bold text-white ${
              hasDanger ? 'bg-danger' : 'bg-warning'
            }`}
          >
            {urgentCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <div
          role="dialog"
          aria-label="Fristen & Erinnerungen"
          className="absolute right-0 mt-2 max-h-[80vh] w-[340px] overflow-y-auto rounded-xl border border-mint bg-white p-4 shadow-lg"
        >
          <div className="mb-3">
            <div className="flex items-center gap-2">
              <h2 className="font-display text-lg font-bold text-ink">Fristen &amp; Erinnerungen</h2>
              <span className="rounded bg-mint px-1.5 py-0.5 text-[10px] font-semibold text-forest">
                Demo
              </span>
            </div>
            <p className="mt-1 text-xs text-slate">
              Beispiel-Wächter aus den Demo-Daten — keine verbindliche Fristauskunft.
            </p>
          </div>

          <ul className="flex flex-col gap-2">
            {REMINDERS.map((reminder) => (
              <li key={reminder.title} className="rounded-lg border border-mint bg-paper p-3">
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className={`h-2 w-2 shrink-0 rounded-full ${SEVERITY_DOT[reminder.severity]}`}
                  />
                  <span className={`text-xs font-semibold ${SEVERITY_TEXT[reminder.severity]}`}>
                    {reminder.tag}
                  </span>
                  <span className="ml-auto text-[11px] whitespace-nowrap text-slate">
                    {reminder.when}
                  </span>
                </div>
                <p className="mt-1.5 text-sm font-semibold text-ink">{reminder.title}</p>
                <p className="mt-0.5 text-xs text-slate">{reminder.detail}</p>
              </li>
            ))}
          </ul>

          <p className="mt-3 text-[11px] text-slate">
            Das vollständige Reminder-/Wächter-Modul folgt separat.
          </p>
        </div>
      ) : null}
    </div>
  );
}
