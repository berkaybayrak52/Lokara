import { WaechterWorkspacePage } from '@/features/waechter/waechter-page';

export default async function WaechterPage({ params }: { params: Promise<{ accountId: string }> }) {
  const { accountId } = await params;
  return <WaechterWorkspacePage accountId={accountId} />;
}
