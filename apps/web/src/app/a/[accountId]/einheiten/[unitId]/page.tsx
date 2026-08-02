import { UnitDetailPage } from '@/features/objekte/unit-detail-page';

export default async function EinheitPage({
  params,
}: {
  params: Promise<{ accountId: string; unitId: string }>;
}) {
  const { accountId, unitId } = await params;
  return <UnitDetailPage accountId={accountId} unitId={unitId} />;
}
