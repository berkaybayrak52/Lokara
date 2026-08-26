import { BuildingWizard } from '@/features/objekte/building-wizard';

export default async function BuildingWizardPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <BuildingWizard accountId={accountId} />;
}
