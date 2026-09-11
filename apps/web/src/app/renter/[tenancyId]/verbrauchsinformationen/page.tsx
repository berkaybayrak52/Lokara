import { RenterDocumentsScreen } from '@/features/renter/renter-documents';

export default async function RenterConsumptionInformationPage({
  params,
}: {
  params: Promise<{ tenancyId: string }>;
}) {
  const { tenancyId } = await params;
  return <RenterDocumentsScreen tenancyId={tenancyId} kind="UVI_ARTIFACT" />;
}
