import { BuildingDetailPage } from '@/features/objekte/building-detail-page';

export default async function ObjektDetailPage({
  params,
}: {
  params: Promise<{ accountId: string; buildingId: string }>;
}) {
  const { accountId, buildingId } = await params;
  return <BuildingDetailPage accountId={accountId} buildingId={buildingId} />;
}
