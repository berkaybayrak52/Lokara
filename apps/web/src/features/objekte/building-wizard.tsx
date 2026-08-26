'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { Button, Card, CardContent, StatusNote } from '@lokara/ui';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { PageHeader } from '@/features/portal/page-header';
import type { BuildingType } from '@/lib/contracts';
import { useFormDraft } from '@/lib/form-draft';

import { FormField } from './form-field';
import { PhotoSlot } from './photo-slot';
import { useCreateBuilding } from './queries';

interface TypeOption {
  value: BuildingType;
  title: string;
  hint: string;
}

const TYPE_OPTIONS: TypeOption[] = [
  { value: 'WOHN_UND_GESCHAEFTSHAUS', title: 'Wohn- und Geschäftshaus', hint: 'Gemischte Nutzung — Wohnen und Gewerbe' },
  { value: 'WOHNHAUS', title: 'Wohnhaus', hint: 'Reines Wohngebäude' },
  { value: 'GEWERBEIMMOBILIE', title: 'Gewerbeimmobilie', hint: 'Überwiegend gewerbliche Nutzung' },
  { value: 'EINFAMILIENHAUS', title: 'Einfamilienhaus', hint: 'Ein Haus, eine Wohneinheit' },
];

const DetailsSchema = z.object({
  name: z.string().min(1, 'Pflichtfeld'),
  street: z.string().min(1, 'Pflichtfeld'),
  houseNumber: z.string().min(1, 'Pflichtfeld'),
  postalCode: z.string().regex(/^\d{5}$/, 'PLZ: genau 5 Ziffern'),
  city: z.string().min(1, 'Pflichtfeld'),
  country: z.string().min(1, 'Pflichtfeld'),
});
type Details = z.infer<typeof DetailsSchema>;

const EMPTY_DETAILS: Details = {
  name: '',
  street: '',
  houseNumber: '',
  postalCode: '',
  city: '',
  country: 'Deutschland',
};

/** Wizard-A (O6): zweistufig — Gebäudeart → Eckdaten — als eigene Seite (kein Modal). */
export function BuildingWizard({ accountId }: { accountId: string }) {
  const router = useRouter();
  const create = useCreateBuilding(accountId);
  const [step, setStep] = useState<1 | 2>(1);
  const [type, setType] = useState<BuildingType | null>(null);
  const [mixedUse, setMixedUse] = useState<'wohnen' | 'gewerbe' | null>(null);

  const form = useForm<Details>({ resolver: zodResolver(DetailsSchema), defaultValues: EMPTY_DETAILS });
  const { draftRestored, clearDraft } = useFormDraft(`${accountId}.building-create`, form);

  const step1Ready = type !== null && (type !== 'WOHN_UND_GESCHAEFTSHAUS' || mixedUse !== null);

  function isResidentialFor(): boolean {
    if (type === 'GEWERBEIMMOBILIE') return false;
    if (type === 'WOHN_UND_GESCHAEFTSHAUS') return mixedUse === 'wohnen';
    return true; // WOHNHAUS, EINFAMILIENHAUS
  }

  const onSubmit = form.handleSubmit((values) => {
    if (type === null) return;
    create.mutate(
      { ...values, buildingType: type, isResidential: isResidentialFor() },
      {
        onSuccess: (building) => {
          clearDraft();
          router.push(`/a/${accountId}/objekte/${building.id}`);
        },
      },
    );
  });

  return (
    <main className="py-10">
      <PageHeader title="Objekt anlegen" description={`Schritt ${step} von 2`} />

      {step === 1 ? (
        <Card className="max-w-2xl">
          <CardContent className="pt-6">
            <fieldset>
              <legend className="mb-3 font-semibold text-ink">Gebäudeart wählen</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {TYPE_OPTIONS.map((option) => {
                  const active = type === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      aria-pressed={active}
                      onClick={() => {
                        setType(option.value);
                        if (option.value !== 'WOHN_UND_GESCHAEFTSHAUS') setMixedUse(null);
                      }}
                      className={
                        'flex flex-col rounded-xl border-l-4 p-4 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ' +
                        (active
                          ? 'border-green bg-mint/60'
                          : 'border-transparent border border-mint hover:bg-mint/40')
                      }
                    >
                      <span className="flex items-center gap-2">
                        <span className={active ? 'font-semibold text-forest' : 'font-semibold text-ink'}>
                          {option.title}
                        </span>
                        {active ? <span className="text-xs font-semibold text-forest">✓ gewählt</span> : null}
                      </span>
                      <span className="mt-1 text-sm text-slate">{option.hint}</span>
                    </button>
                  );
                })}
              </div>
            </fieldset>

            {type === 'WOHN_UND_GESCHAEFTSHAUS' ? (
              <fieldset className="mt-4">
                <legend className="mb-2 text-sm font-semibold text-ink">Überwiegende Nutzung</legend>
                <div className="flex gap-2">
                  {(['wohnen', 'gewerbe'] as const).map((usage) => (
                    <Button
                      key={usage}
                      type="button"
                      variant={mixedUse === usage ? 'default' : 'outline'}
                      size="sm"
                      aria-pressed={mixedUse === usage}
                      onClick={() => setMixedUse(usage)}
                    >
                      {usage === 'wohnen' ? 'Wohnen' : 'Gewerbe'}
                    </Button>
                  ))}
                </div>
              </fieldset>
            ) : null}

            <div className="mt-6">
              <Button type="button" disabled={!step1Ready} onClick={() => setStep(2)}>
                Weiter
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="max-w-2xl">
          <CardContent className="pt-6">
            <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
              <FormField
                id="b-name"
                label="Bezeichnung"
                hint="z. B. Musterstraße 12"
                error={form.formState.errors.name}
                registration={form.register('name')}
              />
              <FormField id="b-street" label="Straße" error={form.formState.errors.street} registration={form.register('street')} />
              <FormField id="b-house" label="Hausnummer" error={form.formState.errors.houseNumber} registration={form.register('houseNumber')} />
              <div className="grid grid-cols-[120px_1fr] gap-4">
                <FormField id="b-plz" label="PLZ" inputMode="numeric" error={form.formState.errors.postalCode} registration={form.register('postalCode')} />
                <FormField id="b-city" label="Ort" error={form.formState.errors.city} registration={form.register('city')} />
              </div>
              <FormField id="b-country" label="Land" error={form.formState.errors.country} registration={form.register('country')} />

              <PhotoSlot />

              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setStep(1)}>
                  Zurück
                </Button>
                <Button type="submit" disabled={create.isPending}>
                  {create.isPending ? 'Wird angelegt…' : 'Objekt anlegen'}
                </Button>
              </div>

              {draftRestored ? (
                <StatusNote kind="warning" label="Entwurf wiederhergestellt.">
                  Ihre letzten Eingaben wurden automatisch gesichert.
                </StatusNote>
              ) : null}
              {create.isError ? (
                <StatusNote kind="danger" label="Anlegen fehlgeschlagen.">
                  Bitte Eingaben prüfen und erneut versuchen.
                </StatusNote>
              ) : null}
            </form>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
