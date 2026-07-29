import { BelegPage } from '@/features/beleg/beleg-page';

export default async function BelegUploadPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <BelegPage accountId={accountId} />;
}
