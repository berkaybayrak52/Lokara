import { MeterWizard } from '@/features/zaehler/meter-wizard';

export default async function NeuerZaehlerPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <MeterWizard accountId={accountId} />;
}
