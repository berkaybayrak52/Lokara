import { Dashboard } from '@/features/portal/dashboard';
import { taxAdvisorLandingPath } from '@/features/portal/app-shell';
import { redirect } from 'next/navigation';

function redirectTaxAdvisorAccountRoot(role: string, accountId: string): void {
  if (role === 'TAX_ADVISOR') redirect(taxAdvisorLandingPath(accountId));
}
void redirectTaxAdvisorAccountRoot;

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <Dashboard accountId={accountId} />;
}
