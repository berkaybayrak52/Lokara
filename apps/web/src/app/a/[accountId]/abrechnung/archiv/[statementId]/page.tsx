import { StatementArchivePage } from '@/features/abrechnung/statement-archive';

export default async function AbrechnungsarchivPage({
  params,
}: {
  params: Promise<{ accountId: string; statementId: string }>;
}) {
  const { accountId, statementId } = await params;
  return <StatementArchivePage accountId={accountId} statementId={statementId} />;
}
