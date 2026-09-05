import { CostsPage } from '@/features/kosten/costs-page';

export default async function KostenPage({
  params,
  searchParams,
}: {
  params: Promise<{ accountId: string }>;
  searchParams: Promise<{ objektId?: string | string[] }>;
}) {
  const { accountId } = await params;
  const query = await searchParams;
  const initialBuildingId =
    typeof query.objektId === 'string' ? query.objektId : (query.objektId?.[0] ?? null);
  return <CostsPage accountId={accountId} initialBuildingId={initialBuildingId} />;
}
