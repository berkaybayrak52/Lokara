import { RenterOverviewScreen } from '@/features/renter/activation';

export default async function RenterOverviewPage({
  params,
}: {
  params: Promise<{ tenancyId: string }>;
}) {
  const { tenancyId } = await params;
  return <RenterOverviewScreen tenancyId={tenancyId} />;
}
