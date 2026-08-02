import { StatementPage } from '@/features/portal/statement';

export default async function AbrechnungPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <StatementPage accountId={accountId} />;
}
