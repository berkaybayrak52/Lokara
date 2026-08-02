import { CostsPage } from '@/features/kosten/costs-page';

export default async function KostenPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <CostsPage accountId={accountId} />;
}
