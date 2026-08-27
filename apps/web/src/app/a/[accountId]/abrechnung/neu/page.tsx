import { StatementStartPage } from '@/features/abrechnung/statement-start';

export default async function NeueAbrechnungPage({
  params,
  searchParams,
}: {
  params: Promise<{ accountId: string }>;
  searchParams: Promise<{ objektId?: string }>;
}) {
  const [{ accountId }, query] = await Promise.all([params, searchParams]);
  return <StatementStartPage accountId={accountId} initialBuildingId={query.objektId} />;
}
