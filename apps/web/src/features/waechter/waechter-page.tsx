'use client';

import { Button, Card, CardContent, CardHeader, CardTitle, Label, StatusNote } from '@lokara/ui';
import React from 'react';

import { useMe } from '@/features/portal/queries';
import { ApiError } from '@/lib/api';

import type { ChecklistApi, GuardApi, M9Role } from './queries';
import { useM9Actions, useM9Data } from './queries';

type Role = M9Role;
type DeliveryStatus =
  'DELIVERED' | 'QUEUED' | 'BOUNCED' | 'COMPLAINED' | 'FAILED' | 'BLOCKED' | 'UNSENT';
interface GuardView {
  id: string;
  code: string;
  stage: string;
  warningDe: string;
  boundaryOn: string | null;
  source: string;
  rechtsstand: string;
  productionBlockers: string[];
  sourceId?: string;
}
interface ReminderView {
  id: string;
  guardCode: string;
  dueOn: string;
  channel: string;
  status: string;
}
interface ScheduleView {
  id: string;
  kind: string;
  enabled: boolean;
  nextOccurrenceOn: string | null;
  blocker?: string;
  buildingId?: string;
  deliveryKind?: string;
  mutationPending?: boolean;
  mutationSuccess?: string;
  mutationError?: string;
}
interface DeliveryView {
  id: string;
  recipient: string;
  status: DeliveryStatus;
  sentAt: string | null;
  blocker?: string;
  mutationError?: string;
  mutationPending?: boolean;
  legallyConfirmed?: boolean;
  deliveredOn?: string | null;
  evidenceReference?: string | null;
  buildingId?: string | null;
  renterId?: string;
  artifactId?: string;
  occurrenceKey?: string | null;
  deliveryKind?: string | null;
  timestampLabel?: string;
  confirmationPending?: boolean;
  confirmationSuccess?: string;
  confirmationError?: string;
}
interface SuppressionView {
  normalizedAddress: string;
  reason: string;
  occurredAt: string;
}
interface ChecklistItemView {
  id: string;
  label: string;
  status: string;
  events: object[];
  mutationPending?: boolean;
  mutationSuccess?: string;
  mutationError?: string;
}
interface ChecklistView {
  id: string;
  title: string;
  templateVersion: string;
  items: ChecklistItemView[];
}
interface WaechterWorkspaceProps {
  accountId: string;
  role: Role;
  guards: GuardView[];
  reminders: ReminderView[];
  schedules: ScheduleView[];
  deliveries: DeliveryView[];
  suppressions: SuppressionView[];
  checklists: ChecklistView[];
  productionChecklistTemplates: object[];
  checklistLibraryBlocker: string;
  onRunGuards?: () => void;
  runPending?: boolean;
  runSuccess?: boolean;
  runError?: string;
  onScheduleChange?: (schedule: ScheduleView, enabled: boolean) => void;
  onChecklistEvent?: (
    checklistId: string,
    itemId: string,
    eventType: 'COMPLETED' | 'REOPENED',
  ) => void;
  onSendDelivery?: (delivery: DeliveryView) => void;
  onConfirmDelivery?: (
    delivery: DeliveryView,
    deliveredOn: string,
    evidenceReference: string,
  ) => void;
}

const DISCLAIMER = 'Lokara ist ein Werkzeug: rechtskonform, keine Rechts- oder Steuerberatung.';
type IconKind = 'check' | 'clock' | 'cross' | 'lock' | 'minus' | 'alert';
const deliveryPresentation: Record<
  DeliveryStatus,
  { label: string; className: string; icon: IconKind }
> = {
  DELIVERED: { label: 'Zugestellt', className: 'bg-mint text-forest', icon: 'check' },
  QUEUED: {
    label: 'In Warteschlange',
    className: 'semantic-yellow-indicator bg-warning-tint text-warning',
    icon: 'clock',
  },
  BOUNCED: { label: 'Unzustellbar', className: 'bg-danger-tint text-danger', icon: 'cross' },
  COMPLAINED: { label: 'Beschwerde', className: 'bg-danger-tint text-danger', icon: 'cross' },
  FAILED: { label: 'Fehlgeschlagen', className: 'bg-danger-tint text-danger', icon: 'cross' },
  BLOCKED: { label: 'Gesperrt', className: 'border border-slate text-ink', icon: 'lock' },
  UNSENT: { label: 'Nicht versendet', className: 'border border-slate text-ink', icon: 'minus' },
};

const guardTitles: Record<string, string> = {
  W1: 'W1 · Abrechnungsfrist',
  W2: 'W2 · Eichfrist',
  W3: 'W3 · Mietrückstand',
  W4: 'W4 · Verbrauchsinformation',
  W5: 'W5 · Vergleichsmiete',
  W6: 'W6 · Staffelmiete',
  W7: 'W7 · Indexmiete',
  W8: 'W8 · Leerstand',
};
const guardBlockerLabels: Record<string, string> = {
  'W1-RENTER-DELIVERY-CONTEXT-MISSING': 'Zustellkontext für die Betriebskostenabrechnung fehlt.',
  'W2-APPROVED-RULE-BUNDLE-MISSING': 'Freigegebenes Regelwerk für die Eichfrist fehlt.',
};
const GUARD_BLOCKER_FALLBACK =
  'Die Rechts- oder Regelgrundlage muss vor dem Produktiveinsatz geprüft werden.';
const DELIVERY_BLOCKER_FALLBACK =
  'Zustellung gesperrt: Das Dokument ist noch nicht für den Versand freigegeben.';
const internalCodePattern = /\b[A-Z][A-Z0-9]*(?:[-_][A-Z0-9]+)+\b/;
const verificationMarkerPattern = /verify-before-production|unsicher/i;

function guardTitle(code: string): string {
  return guardTitles[code] ?? 'Unbekannter Wächter';
}

function guardBlockerLabel(blocker: string): string {
  return (
    guardBlockerLabels[blocker] ??
    (verificationMarkerPattern.test(blocker) || internalCodePattern.test(blocker)
      ? GUARD_BLOCKER_FALLBACK
      : blocker)
  );
}

function reminderChannelLabel(channel: string): string {
  if (channel === 'EMAIL') return 'E-Mail';
  if (channel === 'IN_APP') return 'In der Anwendung';
  return /^[A-Z][A-Z0-9_]*$/.test(channel) ? 'Unbekannter Erinnerungskanal' : channel;
}

function suppressionReasonLabel(reason: string): string {
  if (reason === 'BOUNCED') return 'Unzustellbar';
  if (reason === 'COMPLAINED') return 'Beschwerde';
  return /^[A-Z][A-Z0-9_]*$/.test(reason) ? 'Nicht näher bezeichneter Zustellgrund' : reason;
}

function deliveryBlockerLabel(blocker: string): string {
  return verificationMarkerPattern.test(blocker) || internalCodePattern.test(blocker)
    ? DELIVERY_BLOCKER_FALLBACK
    : blocker;
}

function StatusIcon({ kind }: { kind: IconKind }) {
  const paths: Record<IconKind, React.ReactNode> = {
    check: <path d="m4 8 2.5 2.5L12 5" />,
    clock: (
      <>
        <circle cx="8" cy="8" r="5" />
        <path d="M8 5v3l2 1" />
      </>
    ),
    cross: <path d="m5 5 6 6m0-6-6 6" />,
    lock: (
      <>
        <rect x="4" y="7" width="8" height="6" rx="1" />
        <path d="M6 7V5a2 2 0 0 1 4 0v2" />
      </>
    ),
    minus: <path d="M4 8h8" />,
    alert: (
      <>
        <path d="M8 3 14 13H2L8 3Z" />
        <path d="M8 6v3m0 2h.01" />
      </>
    ),
  };
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 16 16"
      className="size-4 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      {paths[kind]}
    </svg>
  );
}

function guardPresentation(stage: string) {
  if (stage === 'EXPIRED' || stage === 'expired')
    return { label: 'Abgelaufen', icon: 'cross' as const, className: 'bg-danger-tint text-danger' };
  if (stage === 'invalid')
    return { label: 'Fehler', icon: 'cross' as const, className: 'bg-danger-tint text-danger' };
  if (stage === 'basis_year_mismatch')
    return { label: 'Gesperrt', icon: 'lock' as const, className: 'bg-warning-tint text-warning' };
  if (stage === 'source_missing' || stage === 'blocked' || stage === 'Gesperrt')
    return { label: 'Gesperrt', icon: 'lock' as const, className: 'border border-slate text-ink' };
  if (['last_day', '3a', '3b'].includes(stage))
    return { label: 'Dringend', icon: 'alert' as const, className: 'bg-danger-tint text-danger' };
  if (
    [
      'NOTICE',
      'notice',
      'warning',
      'due',
      'overdue',
      'exceeded',
      'expiry_month',
      'reminder_30_days',
      'adjustment_due',
      'opportunity',
      'vacancy',
    ].includes(stage)
  )
    return { label: 'Warnung', icon: 'alert' as const, className: 'bg-warning-tint text-warning' };
  return { label: 'Hinweis', icon: 'clock' as const, className: 'border border-slate text-ink' };
}

function formatDate(value: string | null): string {
  if (!value) return 'Nicht festgelegt';
  const date = new Date(`${value.slice(0, 10)}T00:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium' }).format(date);
}

function DeliveryConfirmationForm({
  delivery,
  onConfirm,
}: {
  delivery: DeliveryView;
  onConfirm: NonNullable<WaechterWorkspaceProps['onConfirmDelivery']>;
}) {
  return (
    <form
      data-action-context={`delivery-confirmation-${delivery.id}`}
      className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        onConfirm(
          delivery,
          String(form.get('deliveredOn') ?? ''),
          String(form.get('evidenceReference') ?? ''),
        );
      }}
    >
      <fieldset name="deliveredOn" data-required="true" disabled={delivery.confirmationPending}>
        <Label htmlFor={`delivered-${delivery.id}`}>Zustelldatum</Label>
        <input
          name="deliveredOn"
          required
          id={`delivered-${delivery.id}`}
          type="date"
          className="mt-1 h-10 w-full rounded-lg border border-slate bg-white px-3 py-2 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        />
      </fieldset>
      <fieldset
        name="evidenceReference"
        data-required="true"
        disabled={delivery.confirmationPending}
      >
        <Label htmlFor={`evidence-${delivery.id}`}>Nachweisreferenz</Label>
        <input
          name="evidenceReference"
          required
          id={`evidence-${delivery.id}`}
          placeholder="Aktenzeichen oder Ablageort"
          className="mt-1 h-10 w-full rounded-lg border border-slate bg-white px-3 py-2 text-sm text-ink placeholder:text-slate focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        />
      </fieldset>
      <div className="sm:col-span-2">
        <Button
          type="submit"
          variant="secondary"
          disabled={delivery.confirmationPending}
          className="focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          Zugang bestätigen
        </Button>
        {delivery.confirmationPending ? (
          <p role="status" className="mt-2 text-sm font-semibold text-ink">
            Zugangsbestätigung wird gespeichert …
          </p>
        ) : null}
        {delivery.confirmationSuccess ? (
          <p role="status" className="mt-2 text-sm font-semibold text-forest">
            {delivery.confirmationSuccess}
          </p>
        ) : null}
        {delivery.confirmationError ? (
          <p role="alert" className="mt-2 text-sm font-semibold text-danger">
            {delivery.confirmationError}
          </p>
        ) : null}
      </div>
    </form>
  );
}

export function WaechterWorkspace(props: WaechterWorkspaceProps) {
  const {
    role,
    guards,
    reminders,
    schedules,
    deliveries,
    suppressions,
    checklists,
    productionChecklistTemplates,
    checklistLibraryBlocker,
    onRunGuards,
    runPending,
    runSuccess,
    runError,
    onScheduleChange,
    onChecklistEvent,
    onSendDelivery,
    onConfirmDelivery,
  } = props;
  const owner = role === 'OWNER';
  const canManageChecklists = owner || role === 'EMPLOYEE';
  return (
    <main className="min-w-0 px-4 py-8 sm:px-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-forest">Fristen und Nachweise</p>
          <h1 className="mt-1 font-display text-3xl font-bold text-ink">Wächter</h1>
          <p className="mt-2 max-w-3xl text-ink">
            Fristen, Zustellstatus und unveränderliche Checklisten-Ereignisse an einem Ort.
          </p>
        </div>
        {owner && onRunGuards ? (
          <div data-action-context="guard-run">
            <Button
              data-primary-action
              disabled={runPending}
              onClick={onRunGuards}
              className="focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              {runPending ? 'Wächter werden ausgewertet …' : 'Wächter neu auswerten'}
            </Button>
          </div>
        ) : null}
      </header>
      {runError ? (
        <StatusNote kind="danger" label="Auswertung fehlgeschlagen" className="mt-4">
          {runError}
        </StatusNote>
      ) : null}
      {runSuccess ? (
        <p role="status" className="mt-4 text-sm font-semibold text-forest">
          Wächterauswertung abgeschlossen.
        </p>
      ) : null}
      <section aria-labelledby="fristen-heading" className="mt-10">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 id="fristen-heading" className="font-display text-2xl font-bold text-ink">
              Fristen
            </h2>
            <p className="mt-1 text-ink">W1–W8 mit der jeweils gespeicherten Regelgrundlage.</p>
          </div>
          <p className="text-sm text-forest">Push-Eskalation: nicht verfügbar (M10)</p>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          {guards.map((guard) => {
            const status = guardPresentation(guard.stage);
            return (
              <Card key={guard.id} className="min-w-0 border-mint">
                <CardHeader className="gap-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle>{guardTitle(guard.code)}</CardTitle>
                    <span
                      data-guard-stage={guard.stage}
                      role="status"
                      aria-label={`Wächterstatus ${guard.code}`}
                      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ${status.className}`}
                    >
                      <StatusIcon kind={status.icon} />
                      {status.label}
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  {guard.warningDe ? (
                    <p className="font-semibold text-ink">{guardBlockerLabel(guard.warningDe)}</p>
                  ) : null}
                  <dl className="mt-4 grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2">
                    <div>
                      <dt className="text-sm font-semibold text-forest">Grenzdatum</dt>
                      <dd className="mt-1 text-ink">{formatDate(guard.boundaryOn)}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-semibold text-forest">Quelle</dt>
                      <dd className="mt-1 break-words text-ink">{guard.source}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-semibold text-forest">Rechtsstand</dt>
                      <dd className="mt-1 text-ink">{guard.rechtsstand}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-semibold text-forest">Produktionssperre</dt>
                      <dd className="mt-1 text-ink">
                        {guard.productionBlockers.length ? (
                          <ul className="list-disc space-y-1 pl-5">
                            {guard.productionBlockers.map((blocker, index) => (
                              <li key={`${guard.id}-blocker-${index}`}>
                                {guardBlockerLabel(blocker)}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          'Keine in dieser Auswertung.'
                        )}
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>
            );
          })}
        </div>
        {guards.length === 0 ? (
          <StatusNote kind="warning" label="Noch keine Auswertung">
            Noch keine Wächterauswertung vorhanden.
          </StatusNote>
        ) : null}
        {owner ? (
          <div className="mt-5">
            <h3 className="font-display text-lg font-semibold text-ink">Erinnerungen</h3>
            {reminders.length ? (
              <ul className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                {reminders.map((reminder) => (
                  <li
                    key={reminder.id}
                    className="rounded-lg border border-mint bg-white p-3 text-ink"
                  >
                    <span className="font-semibold">{reminder.guardCode}</span> ·{' '}
                    {formatDate(reminder.dueOn)} · {reminderChannelLabel(reminder.channel)} ·{' '}
                    {reminder.status}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-ink">Keine offenen Erinnerungen.</p>
            )}
          </div>
        ) : null}
      </section>
      {owner ? (
        <section aria-labelledby="zustellung-heading" className="mt-12">
          <h2 id="zustellung-heading" className="font-display text-2xl font-bold text-ink">
            Zustellung
          </h2>
          <p className="mt-1 max-w-3xl text-ink">
            Automatische Zustellung ist Opt-in und standardmäßig deaktiviert. Echte Anbieter sind
            noch nicht angebunden.
          </p>
          <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {schedules.map((schedule) => (
              <Card key={schedule.id} className="border-mint">
                <CardContent className="pt-6">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="font-display text-lg font-semibold text-ink">
                        {schedule.kind}
                      </h3>
                      <p className="mt-1 text-ink">
                        {schedule.enabled ? 'Aktiviert' : 'Deaktiviert'}
                      </p>
                    </div>
                    {onScheduleChange ? (
                      <div data-action-context={`schedule-${schedule.id}`}>
                        <Button
                          variant="secondary"
                          disabled={schedule.mutationPending}
                          onClick={() => onScheduleChange(schedule, !schedule.enabled)}
                          className="focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                        >
                          {schedule.enabled ? 'Deaktivieren' : 'Opt-in aktivieren'}
                        </Button>
                      </div>
                    ) : null}
                  </div>
                  <p className="mt-3 text-sm text-ink">
                    Nächster Termin: {formatDate(schedule.nextOccurrenceOn)}
                  </p>
                  {schedule.blocker ? (
                    <p className="mt-2 text-sm font-semibold text-ink">{schedule.blocker}</p>
                  ) : null}
                  {schedule.mutationPending ? (
                    <p role="status" className="mt-2 text-sm font-semibold text-ink">
                      Zeitplan wird gespeichert …
                    </p>
                  ) : null}
                  {schedule.mutationSuccess ? (
                    <p role="status" className="mt-2 text-sm font-semibold text-forest">
                      {schedule.mutationSuccess}
                    </p>
                  ) : null}
                  {schedule.mutationError ? (
                    <p role="alert" className="mt-2 text-sm font-semibold text-danger">
                      {schedule.mutationError}
                    </p>
                  ) : null}
                </CardContent>
              </Card>
            ))}
          </div>
          <h3 className="mt-7 font-display text-lg font-semibold text-ink">Versandverlauf</h3>
          <p className="mt-1 text-sm text-ink">
            Provider-Status „Zugestellt“ ist kein Nachweis des rechtlichen Zugangs. W1 wird nur
            durch eine Inhaberbestätigung mit Zustelldatum und Nachweis gelöst.
          </p>
          <ul className="mt-3 space-y-3">
            {deliveries.map((delivery) => {
              const status = deliveryPresentation[delivery.status];
              return (
                <li
                  key={delivery.id}
                  data-delivery-status={delivery.status}
                  className="min-w-0 rounded-lg border border-mint bg-white p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="break-all font-semibold text-ink">{delivery.recipient}</p>
                      <p className="mt-1 text-sm text-ink">
                        {delivery.sentAt
                          ? `${delivery.timestampLabel ?? 'Versandstatus'}: ${formatDate(delivery.sentAt)}`
                          : 'Noch nicht versendet'}
                      </p>
                    </div>
                    <span
                      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ${status.className}`}
                    >
                      <StatusIcon kind={status.icon} />
                      {status.label}
                    </span>
                  </div>
                  {delivery.blocker ? (
                    <p className="mt-2 text-sm font-semibold text-ink">
                      {deliveryBlockerLabel(delivery.blocker)}
                    </p>
                  ) : null}
                  {delivery.mutationError ? (
                    <p role="alert" className="mt-2 text-sm font-semibold text-danger">
                      {delivery.mutationError}
                    </p>
                  ) : null}
                  {delivery.mutationPending ? (
                    <p role="status" className="mt-2 text-sm font-semibold text-ink">
                      Versand wird vorbereitet …
                    </p>
                  ) : null}
                  {delivery.legallyConfirmed ? (
                    <p className="mt-2 text-sm text-forest">
                      Rechtlicher Zugang bestätigt: {formatDate(delivery.deliveredOn ?? null)} ·
                      Nachweis: {delivery.evidenceReference}
                    </p>
                  ) : null}
                  {onSendDelivery && delivery.status === 'UNSENT' ? (
                    <div data-action-context={`delivery-send-${delivery.id}`} className="mt-3">
                      <Button
                        variant="secondary"
                        disabled={delivery.mutationPending}
                        onClick={() => onSendDelivery(delivery)}
                        className="focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                      >
                        Einzeln versenden
                      </Button>
                    </div>
                  ) : null}
                  {!delivery.legallyConfirmed && onConfirmDelivery ? (
                    <DeliveryConfirmationForm delivery={delivery} onConfirm={onConfirmDelivery} />
                  ) : null}
                </li>
              );
            })}
          </ul>
          {deliveries.length === 0 ? (
            <p className="mt-3 text-ink">Noch keine Zustellungen vorhanden.</p>
          ) : null}
          <h3 className="mt-7 font-display text-lg font-semibold text-ink">
            Unterdrückte Empfänger
          </h3>
          {suppressions.length ? (
            <ul className="mt-2 space-y-2">
              {suppressions.map((item, index) => (
                <li
                  key={`${item.normalizedAddress}-${item.occurredAt}-${index}`}
                  className="rounded-lg border border-slate bg-white p-3 text-ink"
                >
                  <span className="break-all font-semibold">{item.normalizedAddress}</span> ·{' '}
                  {suppressionReasonLabel(item.reason)} · {formatDate(item.occurredAt)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-ink">Keine unterdrückten Empfänger.</p>
          )}
        </section>
      ) : null}
      <section aria-labelledby="checklisten-heading" className="mt-12">
        <h2 id="checklisten-heading" className="font-display text-2xl font-bold text-ink">
          Checklisten
        </h2>
        <p className="mt-1 text-ink">Ereignisse werden unveränderlich ergänzt.</p>
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          {checklists.map((checklist) => (
            <Card key={checklist.id} className="border-mint">
              <CardHeader>
                <CardTitle>{checklist.title}</CardTitle>
                <p className="text-sm text-ink">Vorlage {checklist.templateVersion}</p>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {checklist.items.map((item) => (
                    <li key={item.id} className="rounded-lg bg-paper p-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold text-ink">{item.label}</p>
                          <p className="mt-1 text-sm text-ink">Status: {item.status}</p>
                        </div>
                        {canManageChecklists ? (
                          <div data-action-context={`checklist-${checklist.id}-${item.id}`}>
                            <button
                              type="button"
                              disabled={item.mutationPending}
                              onClick={() =>
                                onChecklistEvent?.(
                                  checklist.id,
                                  item.id,
                                  item.status === 'ERLEDIGT' ? 'REOPENED' : 'COMPLETED',
                                )
                              }
                              className="rounded-lg bg-mint px-4 py-2 text-sm font-semibold text-forest transition-opacity duration-200 ease-out hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                            >
                              {item.status === 'ERLEDIGT'
                                ? 'Als offen protokollieren'
                                : 'Als erledigt protokollieren'}
                            </button>
                            {item.mutationPending ? (
                              <p role="status" className="mt-2 text-sm font-semibold text-ink">
                                Checklisten-Ereignis wird gespeichert …
                              </p>
                            ) : null}
                            {item.mutationSuccess ? (
                              <p role="status" className="mt-2 text-sm font-semibold text-forest">
                                {item.mutationSuccess}
                              </p>
                            ) : null}
                            {item.mutationError ? (
                              <p role="alert" className="mt-2 text-sm font-semibold text-danger">
                                {item.mutationError}
                              </p>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
        {productionChecklistTemplates.length === 0 ? (
          <StatusNote kind="warning" label="Keine freigegebene Produktionsvorlage" className="mt-5">
            {checklistLibraryBlocker}
          </StatusNote>
        ) : null}
      </section>
      <p className="mt-10 border-t border-mint pt-4 text-sm text-ink">
        Rechtsstand gemäß jeweiliger Wächterregel. {DISCLAIMER}
      </p>
    </main>
  );
}

function readString(record: Record<string, unknown>, ...keys: string[]): string | null {
  for (const key of keys) if (typeof record[key] === 'string') return record[key] as string;
  return null;
}
function readStrings(record: Record<string, unknown>, ...keys: string[]): string[] {
  for (const key of keys)
    if (Array.isArray(record[key]))
      return (record[key] as unknown[]).filter(
        (value): value is string => typeof value === 'string',
      );
  return [];
}
function evidenceFrom(snapshot: Record<string, unknown>): Record<string, unknown> | null {
  const direct = Array.isArray(snapshot.evidence) ? snapshot.evidence : null;
  if (direct?.[0] && typeof direct[0] === 'object') return direct[0] as Record<string, unknown>;
  const bundle = snapshot.bundle;
  return bundle && typeof bundle === 'object'
    ? evidenceFrom(bundle as Record<string, unknown>)
    : null;
}

export function guardView(row: GuardApi): GuardView {
  const blockers = readStrings(row.resultSnapshot, 'productionBlockers', 'production_blockers');
  const rawStage = readString(row.resultSnapshot, 'stage') ?? '';
  const blocked = rawStage === 'source_missing' || rawStage === 'blocked';
  const evidence = evidenceFrom(row.ruleSnapshot);
  return {
    id: row.id,
    code: row.guardCode,
    stage: blocked ? 'Gesperrt' : rawStage,
    warningDe:
      readString(row.resultSnapshot, 'warningDe', 'warning_de', 'warning') ??
      (blocked ? (blockers[0] ?? '') : ''),
    boundaryOn: readString(
      row.resultSnapshot,
      'boundaryOn',
      'boundary_on',
      'boundaryDate',
      'boundary_date',
    ),
    source:
      (evidence && readString(evidence, 'source')) ??
      readString(row.ruleSnapshot, 'source', 'sourceReference', 'source_reference') ??
      '',
    rechtsstand:
      (evidence && readString(evidence, 'rechtsstand')) ??
      readString(row.ruleSnapshot, 'rechtsstand') ??
      '',
    productionBlockers: blockers,
    sourceId: row.subjectId,
  };
}

function checklistView(row: ChecklistApi): ChecklistView {
  const title = readString(row.templateSnapshot, 'title', 'titleDe', 'title_de') ?? row.templateId;
  const rawItems = Array.isArray(row.templateSnapshot.items) ? row.templateSnapshot.items : [];
  const items = rawItems.flatMap((raw): ChecklistItemView[] => {
    if (!raw || typeof raw !== 'object') return [];
    const item = raw as Record<string, unknown>;
    const id = readString(item, 'id', 'itemId', 'item_id');
    if (!id) return [];
    const events = row.events.filter((event) => event.itemId === id);
    const latest = events.at(-1)?.eventType;
    return [
      {
        id,
        label: readString(item, 'label', 'labelDe', 'label_de') ?? id,
        status: latest === 'COMPLETED' ? 'ERLEDIGT' : 'OFFEN',
        events,
      },
    ];
  });
  return { id: row.id, title, templateVersion: String(row.templateVersion), items };
}
function errorDetail(error: unknown): string | undefined {
  return error instanceof ApiError
    ? (error.detail ?? 'Die Aktion ist fehlgeschlagen.')
    : error instanceof Error
      ? error.message
      : undefined;
}

export function WaechterWorkspacePage({ accountId }: { accountId: string }) {
  const { data: me } = useMe();
  const account = me?.accounts.find((candidate) => candidate.id === accountId);
  const role: Role =
    account?.role === 'OWNER' || account?.role === 'EMPLOYEE' ? account.role : 'TAX_ADVISOR';
  const data = useM9Data(accountId, role);
  const actions = useM9Actions(accountId);
  const queries = [data.guards, data.schedules, data.reminders, data.checklists, data.deliveries];
  if (!me || queries.some((query) => query.isLoading))
    return (
      <main className="px-4 py-12" role="status">
        Wächter werden geladen …
      </main>
    );
  if (queries.some((query) => query.isError))
    return (
      <main className="px-4 py-12">
        <StatusNote kind="danger" label="Laden fehlgeschlagen">
          Die Wächterdaten konnten nicht geladen werden.
        </StatusNote>
      </main>
    );
  const apiDeliveries = data.deliveries.data?.deliveries ?? [];
  const mutationResult = actions.sendDelivery.data;
  const deliveries: DeliveryView[] = apiDeliveries.map((row) => {
    const isMutation = actions.sendDelivery.variables?.artifactId === row.artifactId;
    const returned = mutationResult?.artifactId === row.artifactId ? mutationResult : undefined;
    const blockedReason = returned?.blockedReason ?? row.blockedReason;
    const providerStatus = returned?.providerStatus ?? row.providerStatus;
    const isConfirmation = actions.confirmDelivery.variables?.deliveryId === row.id;
    return {
      id: row.id,
      recipient: returned?.recipient ?? row.recipient ?? 'Nicht hinterlegt',
      status: blockedReason ? 'BLOCKED' : ((providerStatus ?? 'UNSENT') as DeliveryStatus),
      sentAt: row.statusOccurredAt ?? row.attemptedAt,
      timestampLabel: row.statusOccurredAt
        ? 'Statusereignis'
        : row.attemptedAt
          ? 'Versuch'
          : undefined,
      blocker: returned?.blockedDetail ?? row.blockedDetail ?? undefined,
      mutationPending: isMutation && actions.sendDelivery.isPending,
      mutationError: isMutation ? errorDetail(actions.sendDelivery.error) : undefined,
      legallyConfirmed: row.legallyConfirmed,
      deliveredOn: row.deliveredOn,
      evidenceReference: row.evidenceReference,
      buildingId: row.buildingId,
      renterId: row.renterId,
      artifactId: row.artifactId,
      occurrenceKey: row.occurrenceKey,
      deliveryKind: row.deliveryKind,
      confirmationPending: isConfirmation && actions.confirmDelivery.isPending,
      confirmationSuccess:
        isConfirmation && actions.confirmDelivery.isSuccess
          ? 'Rechtlicher Zugang wurde bestätigt.'
          : undefined,
      confirmationError: isConfirmation ? errorDetail(actions.confirmDelivery.error) : undefined,
    };
  });
  const suppressions = apiDeliveries.flatMap((row) => row.suppressionEvents);
  const mappedGuards = (data.guards.data?.guards ?? []).map(guardView);
  const sourceIds = data.guards.data?.sourceIds ?? [];
  const mappedChecklists = (data.checklists.data?.checklists ?? [])
    .map(checklistView)
    .map((checklist) => ({
      ...checklist,
      items: checklist.items.map((item) => {
        const isMutation =
          actions.recordChecklistEvent.variables?.checklistId === checklist.id &&
          actions.recordChecklistEvent.variables.itemId === item.id;
        return {
          ...item,
          mutationPending: isMutation && actions.recordChecklistEvent.isPending,
          mutationSuccess:
            isMutation && actions.recordChecklistEvent.isSuccess
              ? 'Checklisten-Ereignis wurde gespeichert.'
              : undefined,
          mutationError: isMutation ? errorDetail(actions.recordChecklistEvent.error) : undefined,
        };
      }),
    }));
  return (
    <WaechterWorkspace
      accountId={accountId}
      role={role}
      guards={mappedGuards}
      reminders={(data.reminders.data?.reminders ?? []).map((row) => ({
        id: row.id,
        guardCode: row.occurrenceKey.split(':')[0] ?? 'Wächter',
        dueOn: row.dueAt,
        channel: row.channel,
        status: 'Offen',
      }))}
      schedules={(data.schedules.data?.schedules ?? []).map((row) => {
        const buildingId =
          readString(row.scheduleSnapshot, 'statement_archive_id') ?? row.buildingId;
        const isMutation = actions.saveSchedule.variables?.sourceId === buildingId;
        return {
          id: row.id,
          kind: row.deliveryKind === 'UVI' ? 'UVI' : 'Jahresabrechnung',
          enabled: row.enabled,
          nextOccurrenceOn: readString(
            row.scheduleSnapshot,
            'nextOccurrenceOn',
            'next_occurrence_on',
          ),
          blocker: readString(row.scheduleSnapshot, 'blocker') ?? undefined,
          buildingId,
          deliveryKind: row.deliveryKind,
          mutationPending: isMutation && actions.saveSchedule.isPending,
          mutationSuccess:
            isMutation && actions.saveSchedule.isSuccess
              ? 'Zeitplan wurde gespeichert.'
              : undefined,
          mutationError: isMutation ? errorDetail(actions.saveSchedule.error) : undefined,
        };
      })}
      deliveries={deliveries}
      suppressions={suppressions}
      checklists={mappedChecklists}
      productionChecklistTemplates={[]}
      checklistLibraryBlocker={`${data.checklists.data?.blocker ?? 'Kein freigegebener produktiver Checklisten-Katalog vorhanden.'} Page 05 liefert keinen Checklisten-Katalog.`}
      onRunGuards={
        role === 'OWNER' && sourceIds.length
          ? () =>
              actions.runGuards.mutate({
                today: new Date().toISOString().slice(0, 10),
                now: new Date().toISOString(),
                sourceIds: sourceIds,
              })
          : undefined
      }
      runPending={actions.runGuards.isPending}
      runSuccess={actions.runGuards.isSuccess}
      runError={errorDetail(actions.runGuards.error)}
      onScheduleChange={
        role === 'OWNER'
          ? (schedule, enabled) => {
              if (
                !schedule.buildingId ||
                (schedule.deliveryKind !== 'ANNUAL_STATEMENT' && schedule.deliveryKind !== 'UVI')
              )
                return;
              actions.saveSchedule.mutate({
                sourceId: schedule.buildingId,
                deliveryKind: schedule.deliveryKind,
                validFrom: new Date().toISOString().slice(0, 10),
                enabled,
              });
            }
          : undefined
      }
      onChecklistEvent={
        role === 'OWNER' || role === 'EMPLOYEE'
          ? (checklistId, itemId, eventType) =>
              actions.recordChecklistEvent.mutate({
                checklistId,
                itemId,
                body: {
                  eventType,
                  occurredAt: new Date().toISOString(),
                  idempotencyKey: `${checklistId}:${itemId}:${eventType}:${crypto.randomUUID()}`,
                  eventSnapshot: {},
                },
              })
          : undefined
      }
      onSendDelivery={
        role === 'OWNER'
          ? (delivery) => {
              if (
                !delivery.buildingId ||
                !delivery.renterId ||
                !delivery.artifactId ||
                !delivery.occurrenceKey ||
                (delivery.deliveryKind !== 'ANNUAL_STATEMENT' && delivery.deliveryKind !== 'UVI')
              )
                return;
              actions.sendDelivery.mutate({
                buildingId: delivery.buildingId,
                renterId: delivery.renterId,
                artifactId: delivery.artifactId,
                deliveryKind: delivery.deliveryKind,
                occurrenceKey: delivery.occurrenceKey,
              });
            }
          : undefined
      }
      onConfirmDelivery={
        role === 'OWNER'
          ? (delivery, deliveredOn, evidenceReference) =>
              actions.confirmDelivery.mutate({
                deliveryId: delivery.id,
                body: { deliveredOn, evidenceReference },
              })
          : undefined
      }
    />
  );
}
