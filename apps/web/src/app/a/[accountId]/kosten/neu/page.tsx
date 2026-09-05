import { CostWizard } from '@/features/kosten/cost-wizard';

export default async function NeueKostenPage({
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
  return <CostWizard accountId={accountId} initialBuildingId={initialBuildingId} />;
}
