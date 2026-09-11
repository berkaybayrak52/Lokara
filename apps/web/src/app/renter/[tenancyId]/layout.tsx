import { RenterShell } from '@/features/renter/renter-shell';

export default async function RenterLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ tenancyId: string }>;
}) {
  const { tenancyId } = await params;
  return <RenterShell tenancyId={tenancyId}>{children}</RenterShell>;
}
