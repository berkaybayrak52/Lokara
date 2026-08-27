import { StatementWizardPage } from '@/features/abrechnung/statement-wizard';

export default async function AbrechnungsentwurfPage({
  params,
  searchParams,
}: {
  params: Promise<{ accountId: string; draftId: string }>;
  searchParams: Promise<{ step?: string }>;
}) {
  const [{ accountId, draftId }, query] = await Promise.all([params, searchParams]);
  const requestedStep = Number(query.step);
  return (
    <StatementWizardPage
      accountId={accountId}
      draftId={draftId}
      initialStep={Number.isInteger(requestedStep) ? requestedStep : undefined}
    />
  );
}
