import { ZahlungenPage } from '@/features/zahlungen/zahlungen-page';

export default async function ZahlungenRoute({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <ZahlungenPage accountId={accountId} />;
}
