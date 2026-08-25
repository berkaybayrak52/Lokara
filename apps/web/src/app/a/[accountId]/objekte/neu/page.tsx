import { BuildingWizard } from '@/features/objekte/building-wizard';

export default async function NeuesObjektPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <BuildingWizard accountId={accountId} />;
}
