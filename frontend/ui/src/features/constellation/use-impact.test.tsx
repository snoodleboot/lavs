import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';

import { getImpact } from '@/api';
import { queryKeys } from '@/lib';
import { SEED_PRODUCT_ID } from '@/mocks';
import { createTestQueryClient } from '@/test';

import { useImpact } from './use-impact';

function makeWrapper(client: QueryClient): (props: { readonly children: ReactNode }) => ReactNode {
  return function Wrapper({ children }: { readonly children: ReactNode }): ReactNode {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe('useImpact', () => {
  it('does not fetch until a component is selected', () => {
    const client = createTestQueryClient();
    const { result } = renderHook(() => useImpact(SEED_PRODUCT_ID, null), {
      wrapper: makeWrapper(client),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(result.current.data).toBeUndefined();
  });

  it('does not fetch while the product id is undefined', () => {
    const client = createTestQueryClient();
    const { result } = renderHook(() => useImpact(undefined, 'comp-api'), {
      wrapper: makeWrapper(client),
    });

    expect(result.current.fetchStatus).toBe('idle');
  });

  it('returns the blast radius for a selected component under the impact key', async () => {
    const client = createTestQueryClient();
    const { result } = renderHook(() => useImpact(SEED_PRODUCT_ID, 'comp-api'), {
      wrapper: makeWrapper(client),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const levels = new Map(
      result.current.data?.impacted.map((entry) => [
        entry.component_id,
        entry.projected_change_level,
      ]),
    );
    // ui and cli depend on api directly (major → minor); helm depends on ui (→ patch).
    expect(levels.get('comp-ui')).toBe('minor');
    expect(levels.get('comp-cli')).toBe('minor');
    expect(levels.get('comp-helm')).toBe('patch');
    expect(levels.has('comp-api')).toBe(false);

    expect(client.getQueryData(queryKeys.impact(SEED_PRODUCT_ID, 'comp-api'))).toBe(
      result.current.data,
    );
  });
});

describe('getImpact', () => {
  it('maps an unknown product to a not_found error', async () => {
    const result = await getImpact('prod-nope', 'comp-api');

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('not_found');
  });

  it('maps an unknown component to a not_found error', async () => {
    const result = await getImpact('prod-aurora', 'comp-ghost');

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('not_found');
  });
});
