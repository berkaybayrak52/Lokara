import { UnitWizard } from '@/features/objekte/unit-wizard';

export default async function UnitWizardPage({
  params,
}: {
  params: Promise<{ accountId: string; buildingId: string }>;
}) {
  const { accountId, buildingId } = await params;
  return <UnitWizard accountId={accountId} buildingId={buildingId} />;
}
