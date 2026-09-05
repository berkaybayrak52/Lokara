import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={String(href)} {...props}>
      {children}
    </a>
  ),
}));
vi.mock('@/lib/form-draft', () => ({
  useFormDraft: () => ({ draftRestored: false, clearDraft: () => undefined }),
}));
vi.mock('@/features/objekte/queries', () => ({
  useBuildings: () => ({
    isPending: false,
    isError: false,
    data: { buildings: [{ id: 'building-1', name: 'Musterhaus' }] },
  }),
  useBuildingDetail: () => ({ data: { units: [] } }),
}));
vi.mock('./queries', () => ({
  useCostCatalogue: () => ({ isPending: false, isError: true, data: undefined }),
  useCreateCost: () => ({
    mutate: () => undefined,
    reset: () => undefined,
    isPending: false,
    isError: false,
  }),
}));

import { CostWizard } from './cost-wizard';

describe('Kosten erfassen — catalogue failure copy', () => {
  it('does not claim that the unavailable catalogue would select a rechtssichere Kostenart', () => {
    const html = renderToStaticMarkup(
      <CostWizard accountId="account-1" initialBuildingId="building-1" />,
    );

    expect(html).toContain('BetrKV-Katalog konnte nicht geladen werden.');
    expect(html.toLocaleLowerCase('de')).not.toContain('rechtssichere kostenart');
  });
});
