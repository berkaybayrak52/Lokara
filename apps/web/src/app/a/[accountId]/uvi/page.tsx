import { UviPage } from '@/features/uvi/uvi-page';

export default async function UviRoute({ params }: { params: Promise<{ accountId: string }> }) {
  const { accountId } = await params;
  return <UviPage accountId={accountId} />;
}
