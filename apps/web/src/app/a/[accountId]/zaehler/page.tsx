import { MetersPage } from '@/features/zaehler/meters-page';

export default async function ZaehlerPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <MetersPage accountId={accountId} />;
}
