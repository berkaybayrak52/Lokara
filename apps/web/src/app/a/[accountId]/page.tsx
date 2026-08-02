import { Dashboard } from '@/features/portal/dashboard';

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <Dashboard accountId={accountId} />;
}
