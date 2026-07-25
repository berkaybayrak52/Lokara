import { BuildingsPage } from '@/features/objekte/buildings-page';

export default async function ObjektePage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <BuildingsPage accountId={accountId} />;
}
