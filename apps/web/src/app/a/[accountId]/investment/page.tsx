import { InvestmentCockpit } from '@/features/investment/investment-cockpit';

export default async function InvestmentRoute({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <InvestmentCockpit accountId={accountId} />;
}
