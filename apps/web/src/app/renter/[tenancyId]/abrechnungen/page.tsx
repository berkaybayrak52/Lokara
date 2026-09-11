import { RenterDocumentsScreen } from '@/features/renter/renter-documents';

export default async function RenterStatementsPage({
  params,
}: {
  params: Promise<{ tenancyId: string }>;
}) {
  const { tenancyId } = await params;
  return <RenterDocumentsScreen tenancyId={tenancyId} kind="STATEMENT_ARCHIVE" />;
}
