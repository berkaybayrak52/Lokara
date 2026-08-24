import { TaxWorkspacePage } from '@/features/steuern/steuern-page';

export default async function TaxPage({ params }: { params: Promise<{ accountId: string }> }) {
  const { accountId } = await params;
  return <TaxWorkspacePage accountId={accountId} />;
}
