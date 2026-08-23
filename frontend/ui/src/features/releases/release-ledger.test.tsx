import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { SEED_PRODUCT_ID, db, server } from '@/mocks';
import { renderWithProviders } from '@/test';
import type { Release } from '@/types';

import { ReleaseLedger } from './release-ledger';

function makeRelease(): Release {
  return {
    id: 'rel-1',
    product_id: SEED_PRODUCT_ID,
    product_version: '5.1.0',
    label: 'Aurora 5.1',
    created_at: '2026-05-13T12:00:00.000Z',
    bump_level: 'minor',
    bump_rationale: null,
    components: [
      {
        component_id: 'comp-api',
        name: 'lavs-api',
        version_id: 'comp-api-v4',
        version: '2.4.0',
        change_level: 'minor',
      },
      {
        component_id: 'comp-cli',
        name: 'lavs-cli',
        version_id: 'comp-cli-v1',
        version: '1.1.0',
        change_level: null,
      },
    ],
  };
}

describe('ReleaseLedger', () => {
  it('renders the empty state when no releases exist', async () => {
    renderWithProviders(<ReleaseLedger productId={SEED_PRODUCT_ID} />);

    await waitFor(() => expect(screen.getByText(/no releases cut yet/i)).toBeInTheDocument());
    expect(screen.getByText('0 releases')).toBeInTheDocument();
  });

  it('renders release cards and calls onReopen with the release when a card is activated', async () => {
    db.releases = [makeRelease()];
    const onReopen = vi.fn<(release: Release) => void>();
    renderWithProviders(<ReleaseLedger productId={SEED_PRODUCT_ID} onReopen={onReopen} />);

    const card = await screen.findByRole('button', { name: /Aurora 5.1/ });
    expect(card).toHaveTextContent('v5.1.0');
    expect(card).toHaveTextContent('lavs-api 2.4.0');
    expect(screen.getByText('1 release')).toBeInTheDocument();

    await userEvent.click(card);
    expect(onReopen).toHaveBeenCalledTimes(1);
    expect(onReopen.mock.calls[0]?.[0].product_version).toBe('5.1.0');
  });

  it('renders an error state when the ledger fails to load', async () => {
    server.use(
      http.get('*/api/products/:id/releases', () =>
        HttpResponse.json(
          { error: { code: 'unknown', message: 'boom', details: null } },
          { status: 500 },
        ),
      ),
    );
    renderWithProviders(<ReleaseLedger productId={SEED_PRODUCT_ID} />);

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/boom/i));
  });
});
