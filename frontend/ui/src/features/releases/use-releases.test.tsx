import { QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';

import { SEED_PRODUCT_ID, db } from '@/mocks';
import { createTestQueryClient } from '@/test';
import type { Release } from '@/types';

import { useRelease, useReleases } from './use-releases';

function makeWrapper(): (props: { children: ReactNode }) => ReactNode {
  const client = createTestQueryClient();
  return function Wrapper({ children }: { children: ReactNode }): ReactNode {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

const RELEASE: Release = {
  id: 'rel-1',
  product_id: SEED_PRODUCT_ID,
  product_version: '5.1.0',
  label: 'Aurora 5.1',
  created_at: '2026-05-13T12:00:00.000Z',
  bump_level: 'minor',
  bump_rationale: null,
  components: [],
};

describe('useReleases / useRelease', () => {
  it('does not fetch while the product id is undefined', () => {
    const { result } = renderHook(() => useReleases(undefined), { wrapper: makeWrapper() });
    expect(result.current.fetchStatus).toBe('idle');
    expect(result.current.data).toBeUndefined();
  });

  it('fetches a single release by id', async () => {
    db.releases = [RELEASE];
    const { result } = renderHook(() => useRelease('rel-1'), { wrapper: makeWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.product_version).toBe('5.1.0');
  });

  it('stays idle when no release id is given', () => {
    const { result } = renderHook(() => useRelease(undefined), { wrapper: makeWrapper() });
    expect(result.current.fetchStatus).toBe('idle');
  });
});
