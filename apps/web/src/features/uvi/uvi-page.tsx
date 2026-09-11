'use client';

import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, StatusNote } from '@lokara/ui';
import { useMutation } from '@tanstack/react-query';
import React, { useRef, useState } from 'react';
import { z } from 'zod';

import { useMe } from '@/features/portal/queries';
import { useMeterWorkspace } from '@/features/zaehler/queries';
import { api, API_URL, ApiError } from '@/lib/api';
import type { MeterWorkspaceResponse } from '@/lib/contracts';
import { isDemoPreview } from '@/lib/demo-preview';

const UviRunSchema = z.object({
  runId: z.string().min(1),
  documentUrl: z.string().min(1),
  productionBlocked: z.boolean(),
  unresolvedConflicts: z.array(z.string()),
});
const UviInputSchema = z.object({
  tenancyId: z.string().min(1),
  targetMonth: z.string().regex(/^\d{4}-(0[1-9]|1[0-2])-01$/),
});

function previousMonth(asOf: string): string {
  const date = new Date(asOf);
  date.setUTCMonth(date.getUTCMonth() - 1, 1);
  return date.toISOString().slice(0, 7);
}

function dateLabel(value: string): string {
  return value.split('-').reverse().join('.');
}

export function UviPage({ accountId }: { accountId: string }) {
  const me = useMe();
  const account = me.data?.accounts.find((candidate) => candidate.id === accountId);

  return (
    <main className="min-w-0 space-y-8 py-8 [overflow-wrap:anywhere]">
      <header className="max-w-3xl space-y-2 pr-12">
        <h1 className="font-display text-2xl font-semibold text-ink sm:text-3xl">
          Verbrauchsinformation (UVI)
        </h1>
        <p className="text-base leading-relaxed text-slate">
          Monatliche Verbrauchsinformation erstellen oder das bereits archivierte PDF öffnen.
        </p>
      </header>
      {me.isPending ? (
        <p role="status">Kontozugriff wird geladen …</p>
      ) : me.isError ? (
        <div className="space-y-4">
          <StatusNote kind="danger" label="Kontozugriff konnte nicht geladen werden." />
          <Button variant="outline" onClick={() => void me.refetch()}>Erneut versuchen</Button>
        </div>
      ) : account?.role !== 'OWNER' ? (
        <StatusNote kind="warning" label="Nur für Inhaber:innen verfügbar.">
          Für dieses Konto können Sie keine Verbrauchsinformation erstellen oder öffnen.
        </StatusNote>
      ) : (
        <OwnerUviWorkspace key={accountId} accountId={accountId} />
      )}
    </main>
  );
}

function OwnerUviWorkspace({ accountId }: { accountId: string }) {
  const workspace = useMeterWorkspace(accountId);
  const preview = isDemoPreview();
  if (preview) {
    return (
      <div className="max-w-3xl space-y-4">
        <StatusNote kind="warning" label="Vorschau – keine UVI-Erstellung.">
          Die Portfolio-Vorschau enthält keine monatlichen UVI-Daten. Hier wird kein PDF erstellt.
        </StatusNote>
        {process.env.NEXT_PUBLIC_DEMO_PREVIEW === 'true' ? (
          <p className="text-sm leading-relaxed text-ink">
            Die Vorschau ist in dieser Umgebung fest aktiviert. Live-Daten sind erst nach
            Deaktivierung dieser Einstellung verfügbar.
          </p>
        ) : (
          <Button asChild variant="outline" className="h-auto min-h-10 max-w-full whitespace-normal">
            <a href={`/a/${encodeURIComponent(accountId)}/uvi?preview=0`}>Live-Daten öffnen</a>
          </Button>
        )}
      </div>
    );
  }
  if (workspace.isPending) {
    return (
      <div className="max-w-3xl space-y-4" role="status" aria-busy="true">
        <p>Objekte und Mietverhältnisse werden geladen …</p>
        <div className="h-48 rounded-lg bg-mint" aria-hidden="true" />
      </div>
    );
  }
  if (workspace.isError || !workspace.data) {
    return (
      <div className="max-w-3xl space-y-4">
        <StatusNote kind="danger" label="UVI-Auswahl konnte nicht geladen werden." />
        <Button variant="outline" onClick={() => void workspace.refetch()}>Erneut versuchen</Button>
      </div>
    );
  }
  if (workspace.data.buildings.length === 0) {
    return <p role="status">Noch keine Objekte vorhanden. Legen Sie zuerst ein Objekt im Bereich „Objekte“ an.</p>;
  }
  return <UviForm accountId={accountId} workspace={workspace.data} />;
}

function UviForm({ accountId, workspace }: { accountId: string; workspace: MeterWorkspaceResponse }) {
  const [buildingId, setBuildingId] = useState('');
  const [unitId, setUnitId] = useState('');
  const [tenancyId, setTenancyId] = useState('');
  const [month, setMonth] = useState(() => previousMonth(workspace.asOf));
  const [revision, setRevision] = useState(0);
  const inFlight = useRef(false);
  const building = workspace.buildings.find((candidate) => candidate.id === buildingId);
  const unit = building?.units.find((candidate) => candidate.id === unitId);
  const tenancy = unit?.tenancies.find((candidate) => candidate.id === tenancyId);
  const input = UviInputSchema.safeParse({ tenancyId, targetMonth: `${month}-01` });
  const mutation = useMutation({
    mutationFn: async (selection: { buildingId: string; tenancyId: string; month: string; revision: number }) => {
      // Recheck at submission in case preview was activated after the form loaded.
      if (isDemoPreview()) throw new Error('Preview writes are disabled');
      const path = `/a/${encodeURIComponent(accountId)}/buildings/${encodeURIComponent(selection.buildingId)}/uvi-runs`;
      const body = UviInputSchema.parse({ tenancyId: selection.tenancyId, targetMonth: `${selection.month}-01` });
      const run = await api(path, UviRunSchema, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      // Do not trust a returned URL to point outside this account/building/run.
      if (run.documentUrl !== `${path}/${encodeURIComponent(run.runId)}/document`) {
        throw new Error('Unexpected UVI document scope');
      }
      return { run, revision: selection.revision };
    },
    retry: false,
    onSettled: () => { inFlight.current = false; },
  });
  const result = mutation.data?.revision === revision ? mutation.data.run : undefined;
  const error = mutation.variables?.revision === revision ? mutation.error : null;
  function changed() { setRevision((value) => value + 1); }

  return (
    <div className="max-w-3xl space-y-8">
      <Card>
        <CardHeader className="p-4 sm:p-6"><CardTitle className="leading-snug">Monat und Mietverhältnis auswählen</CardTitle></CardHeader>
        <CardContent className="px-4 sm:px-6">
          <form className="space-y-6" onSubmit={(event) => {
            event.preventDefault();
            if (inFlight.current || mutation.isPending || !building || !unit || !tenancy || !input.success || isDemoPreview()) return;
            inFlight.current = true;
            mutation.mutate({ buildingId, tenancyId, month, revision });
          }}>
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="min-w-0 space-y-2">
                <Label htmlFor="uvi-building">Objekt</Label>
                <Select id="uvi-building" className="min-w-0" value={buildingId} required onChange={(event) => {
                  setBuildingId(event.target.value); setUnitId(''); setTenancyId(''); changed();
                }}>
                  <option value="">Objekt auswählen</option>
                  {workspace.buildings.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.address}</option>)}
                </Select>
              </div>
              <div className="min-w-0 space-y-2">
                <Label htmlFor="uvi-unit">Einheit</Label>
                <Select id="uvi-unit" className="min-w-0" value={unitId} required disabled={!building || !building.units.length} onChange={(event) => {
                  setUnitId(event.target.value); setTenancyId(''); changed();
                }}>
                  <option value="">Einheit auswählen</option>
                  {building?.units.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                </Select>
                {building && !building.units.length && <p className="text-sm text-slate">Dieses Objekt hat noch keine Einheiten.</p>}
              </div>
              <div className="min-w-0 space-y-2 sm:col-span-2">
                <Label htmlFor="uvi-tenancy">Mietverhältnis</Label>
                <Select id="uvi-tenancy" className="min-w-0" value={tenancyId} required disabled={!unit || !unit.tenancies.length} onChange={(event) => {
                  setTenancyId(event.target.value); changed();
                }}>
                  <option value="">Mietverhältnis auswählen</option>
                  {unit?.tenancies.map((item) => <option key={item.id} value={item.id}>{item.label} · {dateLabel(item.validFrom)} – {item.validTo ? dateLabel(item.validTo) : 'unbefristet'}</option>)}
                </Select>
                {unit && !unit.tenancies.length && <p className="text-sm text-slate">Für diese Einheit ist noch kein Mietverhältnis hinterlegt.</p>}
              </div>
              <div className="min-w-0 space-y-2">
                <Label htmlFor="uvi-month">Monat</Label>
                <Input id="uvi-month" className="min-w-0" type="month" value={month} required onChange={(event) => { setMonth(event.target.value); changed(); }} />
              </div>
            </div>
            <p className="text-sm leading-relaxed text-slate">
              Grundlage sind die gespeicherten Monatsablesungen und die UVI-Gebäudekonfiguration.
              Ein vorhandenes Archiv für dieses Mietverhältnis und diesen Monat wird erneut geöffnet.
            </p>
            <Button type="submit" className="h-auto min-h-10 max-w-full whitespace-normal" disabled={!building || !unit || !tenancy || !input.success || mutation.isPending}>
              {mutation.isPending ? 'UVI wird geöffnet …' : 'UVI erstellen / öffnen'}
            </Button>
            {mutation.isPending && <p role="status" className="text-sm text-slate">Die Anfrage wird verarbeitet. Es wird keine E-Mail versendet.</p>}
          </form>
        </CardContent>
      </Card>
      {error && <StatusNote kind="danger" label="UVI konnte nicht geöffnet werden.">
        {error instanceof ApiError && error.detail ? error.detail : 'Bitte versuchen Sie es erneut. Prüfen Sie bei anhaltenden Fehlern die Monatsdaten und den Kontozugriff.'}
      </StatusNote>}
      {result && (
        <section aria-labelledby="uvi-result-title" className="space-y-4" aria-live="polite">
          <h2 id="uvi-result-title" className="font-display text-xl font-semibold text-ink">Archiviertes PDF verfügbar</h2>
          {result.productionBlocked && <StatusNote kind="warning" label="Nicht für den produktiven Versand freigegeben">
            Das PDF dient der Prüfung. Ein Download hebt die offenen Freigaben nicht auf.
          </StatusNote>}
          {result.unresolvedConflicts.length > 0 && (
            <div className="space-y-2 text-sm leading-relaxed text-ink">
              <h3 className="font-semibold">Offene Hinweise und Freigaben</h3>
              <ul className="list-disc space-y-2 pl-6">
                {result.unresolvedConflicts.map((conflict, index) => <li key={`${index}:${conflict}`} className="break-words">{conflict}</li>)}
              </ul>
            </div>
          )}
          <Button asChild variant="outline" className="h-auto min-h-10 max-w-full whitespace-normal"><a href={`${API_URL}${result.documentUrl}`}>PDF herunterladen</a></Button>
        </section>
      )}
      <p className="text-sm leading-relaxed text-slate">Es wird keine E-Mail versendet. Eine Veröffentlichung im Mieterportal erfolgt nicht.</p>
    </div>
  );
}
