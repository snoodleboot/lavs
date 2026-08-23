import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';

import { getGraph } from '@/api';
import { queryKeys } from '@/lib';
import { SEED_PRODUCT_ID, seedDependencies } from '@/mocks';
import { createTestQueryClient } from '@/test';

import { useGraph } from './use-graph';

function makeWrapper(client: QueryClient): (props: { readonly children: ReactNode }) => ReactNode {
  return function Wrapper({ children }: { readonly children: ReactNode }): ReactNode {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe('useGraph', () => {
  it('loads the product graph and keys it under queryKeys.graph', async () => {
    const client = createTestQueryClient();
    const { result } = renderHook(() => useGraph(SEED_PRODUCT_ID), {
      wrapper: makeWrapper(client),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.edges).toHaveLength(seedDependencies().length);
    expect(result.current.data?.nodes).toHaveLength(4);
    expect(client.getQueryData(queryKeys.graph(SEED_PRODUCT_ID))).toBe(result.current.data);
  });

  it('does not fetch while the product id is undefined', () => {
    const client = createTestQueryClient();
    const { result } = renderHook(() => useGraph(undefined), { wrapper: makeWrapper(client) });

    expect(result.current.fetchStatus).toBe('idle');
    expect(result.current.data).toBeUndefined();
    expect(client.getQueryData(queryKeys.graph('none'))).toBeUndefined();
  });
});

describe('getGraph', () => {
  it('maps an unknown product to a not_found error', async () => {
    const result = await getGraph('prod-nope');

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('not_found');
  });
});
