import { UnitWizardPage } from '@/features/objekte/unit-wizard';

export default async function NeueEinheitPage({
  params,
}: {
  params: Promise<{ accountId: string; buildingId: string }>;
}) {
  const { accountId, buildingId } = await params;
  return <UnitWizardPage accountId={accountId} buildingId={buildingId} />;
}
