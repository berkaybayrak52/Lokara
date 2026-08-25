import { BrandedState, OverviewLink } from '@/features/portal/branded-state';

export default function NotFoundPage() {
  return (
    <BrandedState
      title="Seite nicht gefunden"
      description="Die angeforderte Adresse existiert nicht oder ist nicht mehr verfügbar."
      action={<OverviewLink />}
    />
  );
}
