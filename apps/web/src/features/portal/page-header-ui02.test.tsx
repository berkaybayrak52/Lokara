import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { PageHeader } from './page-header';

describe('UI-02 shared page header', () => {
  it('renders exactly one h1 while preserving all optional content slots', () => {
    const html = renderToStaticMarkup(
      <PageHeader
        breadcrumb={<a href="/a/account-1/objekte">Objekte</a>}
        title="Musterhaus"
        description="Objektakte und Einheiten im Überblick."
        status={<span>Aktiv</span>}
        actions={<button type="button">Bearbeiten</button>}
      />,
    );

    expect(html.match(/<h1(?:\s|>)/g)).toHaveLength(1);
    expect(html.match(/<\/h1>/g)).toHaveLength(1);
    expect(html).toContain('Objekte');
    expect(html).toContain('Musterhaus');
    expect(html).toContain('Objektakte und Einheiten im Überblick.');
    expect(html).toContain('Aktiv');
    expect(html).toContain('Bearbeiten');
  });

  it('allows a title-only header without inventing empty landmarks or actions', () => {
    const html = renderToStaticMarkup(<PageHeader title="Kosten" />);

    expect(html.match(/<h1(?:\s|>)/g)).toHaveLength(1);
    expect(html).toContain('Kosten');
    expect(html).not.toContain('<p');
    expect(html).not.toContain('<button');
  });
});
