'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  StatusNote,
} from '@lokara/ui';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { PageHeader } from '@/features/portal/page-header';
import { useFormDraft } from '@/lib/form-draft';

import { FormField } from './form-field';
import { InactivePhotoSlot } from './inactive-photo-slot';
import { useCreateBuilding } from './queries';

const BUILDING_TYPES = [
  'WOHN_UND_GESCHAEFTSHAUS',
  'WOHNHAUS',
  'GEWERBEIMMOBILIE',
  'EINFAMILIENHAUS',
] as const;

type BuildingType = (typeof BUILDING_TYPES)[number];
type PredominantUse = 'RESIDENTIAL' | 'COMMERCIAL';

const BuildingFormSchema = z
  .object({
    buildingType: z.enum(BUILDING_TYPES).or(z.literal('')),
    predominantUse: z.enum(['RESIDENTIAL', 'COMMERCIAL']).or(z.literal('')),
    name: z.string().trim().min(1, 'Pflichtfeld').max(200, 'Maximal 200 Zeichen'),
    street: z.string().trim().min(1, 'Pflichtfeld').max(200, 'Maximal 200 Zeichen'),
    houseNumber: z.string().trim().min(1, 'Pflichtfeld').max(20, 'Maximal 20 Zeichen'),
    postalCode: z.string().regex(/^\d{5}$/, 'PLZ: genau 5 Ziffern'),
    city: z.string().trim().min(1, 'Pflichtfeld').max(100, 'Maximal 100 Zeichen'),
    country: z.string().trim().min(1, 'Pflichtfeld').max(100, 'Maximal 100 Zeichen'),
  })
  .superRefine((values, context) => {
    if (values.buildingType === '') {
      context.addIssue({ code: 'custom', path: ['buildingType'], message: 'Pflichtfeld' });
    }
    if (`${values.street} ${values.houseNumber}`.length > 200) {
      context.addIssue({
        code: 'custom',
        path: ['houseNumber'],
        message: 'Straße und Hausnummer dürfen zusammen maximal 200 Zeichen haben',
      });
    }
  });

type BuildingForm = z.infer<typeof BuildingFormSchema>;

const EMPTY: BuildingForm = {
  buildingType: '',
  predominantUse: '',
  name: '',
  street: '',
  houseNumber: '',
  postalCode: '',
  city: '',
  country: 'Deutschland',
};

const TYPE_OPTIONS: Array<{ value: BuildingType; title: string; description: string }> = [
  {
    value: 'WOHN_UND_GESCHAEFTSHAUS',
    title: 'Wohn- und Geschäftshaus',
    description: 'Gemischte Nutzung — Wohnen und Gewerbe',
  },
  { value: 'WOHNHAUS', title: 'Wohnhaus', description: 'Reines Wohngebäude' },
  {
    value: 'GEWERBEIMMOBILIE',
    title: 'Gewerbeimmobilie',
    description: 'Überwiegend gewerbliche Nutzung',
  },
  {
    value: 'EINFAMILIENHAUS',
    title: 'Einfamilienhaus',
    description: 'Ein Haus, eine Wohneinheit',
  },
];

export function BuildingWizard({ accountId }: { accountId: string }) {
  const router = useRouter();
  const create = useCreateBuilding(accountId);
  const [step, setStep] = useState<1 | 2>(1);
  const form = useForm<BuildingForm>({
    resolver: zodResolver(BuildingFormSchema),
    defaultValues: EMPTY,
  });
  const { draftRestored, clearDraft } = useFormDraft(`${accountId}.building-create`, form);
  const buildingType = form.watch('buildingType');
  const predominantUse = form.watch('predominantUse');
  const mixedUseIncomplete = buildingType === 'WOHN_UND_GESCHAEFTSHAUS' && predominantUse === '';

  const onSubmit = form.handleSubmit((values) => {
    if (values.buildingType === '') return;
    const isResidential =
      values.buildingType === 'WOHNHAUS' ||
      values.buildingType === 'EINFAMILIENHAUS' ||
      (values.buildingType === 'WOHN_UND_GESCHAEFTSHAUS' &&
        values.predominantUse === 'RESIDENTIAL');
    create.mutate(
      {
        name: values.name,
        street: values.street,
        houseNumber: values.houseNumber,
        postalCode: values.postalCode,
        city: values.city,
        country: values.country,
        buildingType: values.buildingType,
        isResidential,
      },
      {
        onSuccess: (created) => {
          clearDraft();
          router.push(`/a/${accountId}/objekte/${created.id}`);
        },
      },
    );
  });

  return (
    <main className="py-10">
      <PageHeader
        title="Objekt anlegen"
        description={`Schritt ${step} von 2`}
        breadcrumb={
          <Link
            className="text-green underline-offset-4 hover:underline"
            href={`/a/${accountId}/objekte`}
          >
            Objekte
          </Link>
        }
      />

      <Card className="max-w-3xl">
        {step === 1 ? (
          <>
            <CardHeader>
              <CardTitle>Gebäudeart</CardTitle>
              <CardDescription>
                Wählen Sie die Art, die das Objekt am besten beschreibt.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-6">
              {buildingType === 'WOHN_UND_GESCHAEFTSHAUS' ? (
                <fieldset className="order-2">
                  <legend className="mb-2 font-display font-semibold text-ink">
                    Überwiegende Nutzung
                  </legend>
                  <div className="flex flex-wrap gap-3">
                    {(
                      [
                        ['RESIDENTIAL', 'Wohnen'],
                        ['COMMERCIAL', 'Gewerbe'],
                      ] as const
                    ).map(([value, label]) => (
                      <label
                        key={value}
                        className="rounded-lg border border-slate/40 px-4 py-3 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring"
                      >
                        <input
                          type="radio"
                          value={value satisfies PredominantUse}
                          {...form.register('predominantUse')}
                          className="mr-2 accent-green"
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </fieldset>
              ) : null}

              <fieldset className="order-1 grid gap-3 sm:grid-cols-2">
                <legend className="sr-only">Gebäudeart</legend>
                {TYPE_OPTIONS.map((option) => {
                  const selected = buildingType === option.value;
                  return (
                    <label
                      key={option.value}
                      className={`cursor-pointer rounded-xl border p-4 transition-colors duration-150 ease-out focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring motion-reduce:transition-none ${
                        selected
                          ? 'border-green bg-mint/50 text-forest'
                          : 'border-slate/40 bg-paper'
                      }`}
                    >
                      <input
                        type="radio"
                        value={option.value}
                        {...form.register('buildingType')}
                        className="mr-3 accent-green"
                      />
                      <span className="font-display font-semibold">{option.title}</span>
                      {selected ? (
                        <span className="ml-2 text-sm font-semibold">Ausgewählt</span>
                      ) : null}
                      <span className="mt-2 block text-sm text-slate">{option.description}</span>
                    </label>
                  );
                })}
              </fieldset>

              <Button
                type="button"
                className="order-3 self-start"
                disabled={buildingType === '' || mixedUseIncomplete}
                onClick={() => setStep(2)}
              >
                Weiter
              </Button>
              {draftRestored ? (
                <StatusNote className="order-4" kind="warning" label="Entwurf wiederhergestellt.">
                  Ihre letzten Eingaben wurden automatisch gesichert.
                </StatusNote>
              ) : null}
            </CardContent>
          </>
        ) : (
          <>
            <CardHeader>
              <CardTitle>Eckdaten</CardTitle>
              <CardDescription>Adresse und Bezeichnung des neuen Objekts.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
                <FormField
                  id="building-name"
                  label="Bezeichnung"
                  hint="z. B. Musterstraße 12"
                  error={form.formState.errors.name}
                  registration={form.register('name')}
                />
                <FormField
                  id="building-street"
                  label="Straße"
                  error={form.formState.errors.street}
                  registration={form.register('street')}
                />
                <FormField
                  id="building-house-number"
                  label="Hausnummer"
                  error={form.formState.errors.houseNumber}
                  registration={form.register('houseNumber')}
                />
                <FormField
                  id="building-postal-code"
                  label="PLZ"
                  inputMode="numeric"
                  error={form.formState.errors.postalCode}
                  registration={form.register('postalCode')}
                />
                <FormField
                  id="building-city"
                  label="Ort"
                  error={form.formState.errors.city}
                  registration={form.register('city')}
                />
                <FormField
                  id="building-country"
                  label="Land"
                  error={form.formState.errors.country}
                  registration={form.register('country')}
                />
                <InactivePhotoSlot />
                <div className="flex flex-wrap gap-3">
                  <Button type="button" variant="outline" onClick={() => setStep(1)}>
                    Zurück
                  </Button>
                  <Button type="submit" disabled={create.isPending}>
                    {create.isPending ? 'Wird angelegt…' : 'Objekt anlegen'}
                  </Button>
                </div>
                {create.isError ? (
                  <StatusNote kind="danger" label="Anlegen fehlgeschlagen.">
                    Bitte Eingaben prüfen und erneut versuchen.
                  </StatusNote>
                ) : null}
              </form>
            </CardContent>
          </>
        )}
      </Card>
    </main>
  );
}
