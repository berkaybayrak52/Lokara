import { StatementListPage } from '@/features/abrechnung/statement-list';

export default async function AbrechnungPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <StatementListPage accountId={accountId} />;
}
