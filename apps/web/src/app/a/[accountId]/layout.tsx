import { AppShell } from '@/features/portal/app-shell';

/** URL-carried account context (docs/04): /a/{accountId}/… — never the session. */
export default async function PortalLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  return <AppShell accountId={accountId}>{children}</AppShell>;
}
