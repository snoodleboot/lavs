import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { queryKeys } from '@/lib';
import { SEED_PRODUCT_ID, seedComponents, seedProduct } from '@/mocks';
import { createTestQueryClient } from '@/test';
import type { Release, Timeline, Version } from '@/types';

import { FakeEventSource } from './fake-event-source';
import { useProductEvents } from './use-product-events';

function seedTimeline(client: QueryClient): Timeline {
  const timeline: Timeline = { product: seedProduct(), components: seedComponents() };
  client.setQueryData(queryKeys.timeline(SEED_PRODUCT_ID), timeline);
  return timeline;
}

function wrapper(client: QueryClient): (props: { readonly children: ReactNode }) => ReactNode {
  return function Wrapper({ children }: { readonly children: ReactNode }): ReactNode {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

const NEW_VERSION: Version = {
  id: 'comp-api-v5',
  component_id: 'comp-api',
  major: 2,
  minor: 5,
  patch: 0,
  prerelease: null,
  status: 'active',
  created_at: '2026-05-13T12:00:00.000Z',
};

const NEW_RELEASE: Release = {
  id: 'rel-1',
  product_id: SEED_PRODUCT_ID,
  product_version: '5.1.0',
  label: 'Aurora 5.1',
  created_at: '2026-05-13T12:00:00.000Z',
  bump_level: 'minor',
  bump_rationale: null,
  components: [],
};

describe('useProductEvents', () => {
  let client: QueryClient;
  let fake: FakeEventSource;

  beforeEach(() => {
    client = createTestQueryClient();
    fake = new FakeEventSource('sse://aurora');
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const factory = (): ((url: string) => EventSource) => (url: string) => {
    fake = new FakeEventSource(url);
    return fake as unknown as EventSource;
  };

  it('is a no-op when productId is undefined', () => {
    const eventSourceFactory = vi.fn(() => fake as unknown as EventSource);
    const { result } = renderHook(() => useProductEvents(undefined, { eventSourceFactory }), {
      wrapper: wrapper(client),
    });

    expect(eventSourceFactory).not.toHaveBeenCalled();
    expect(result.current.connected).toBe(false);
    expect(result.current.freshVersionIds.size).toBe(0);
  });

  it('applies version.created to the timeline cache and flags a fresh id', () => {
    seedTimeline(client);
    const make = factory();
    const { result } = renderHook(
      () => useProductEvents(SEED_PRODUCT_ID, { eventSourceFactory: make }),
      { wrapper: wrapper(client) },
    );

    act(() => fake.emit('version.created', { component_id: 'comp-api', version: NEW_VERSION }));

    const timeline = client.getQueryData<Timeline>(queryKeys.timeline(SEED_PRODUCT_ID));
    const api = timeline?.components.find((component) => component.id === 'comp-api');
    expect(api?.versions).toHaveLength(6);
    expect(api?.versions.at(-1)).toMatchObject({ id: 'comp-api-v5', status: 'active' });
    expect(result.current.freshVersionIds.has('comp-api-v5')).toBe(true);
  });

  it('clears the fresh id after the pulse delay', () => {
    vi.useFakeTimers();
    seedTimeline(client);
    const make = factory();
    const { result } = renderHook(
      () => useProductEvents(SEED_PRODUCT_ID, { eventSourceFactory: make }),
      { wrapper: wrapper(client) },
    );

    act(() => fake.emit('version.created', { component_id: 'comp-api', version: NEW_VERSION }));
    expect(result.current.freshVersionIds.has('comp-api-v5')).toBe(true);

    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(result.current.freshVersionIds.has('comp-api-v5')).toBe(false);
  });

  it('applies version.rolled_back and flags the rolled-back id', () => {
    seedTimeline(client);
    const make = factory();
    const { result } = renderHook(
      () => useProductEvents(SEED_PRODUCT_ID, { eventSourceFactory: make }),
      { wrapper: wrapper(client) },
    );

    act(() =>
      fake.emit('version.rolled_back', {
        component_id: 'comp-api',
        version_id: 'comp-api-v4',
        reactivated_version_id: 'comp-api-v3',
      }),
    );

    const timeline = client.getQueryData<Timeline>(queryKeys.timeline(SEED_PRODUCT_ID));
    const api = timeline?.components.find((component) => component.id === 'comp-api');
    expect(api?.versions.find((version) => version.id === 'comp-api-v4')?.status).toBe(
      'rolled_back',
    );
    expect(api?.versions.find((version) => version.id === 'comp-api-v3')?.status).toBe('active');
    expect(result.current.rolledBackVersionIds.has('comp-api-v4')).toBe(true);
  });

  it('records release.cut in state and cache', () => {
    seedTimeline(client);
    client.setQueryData(queryKeys.releases(SEED_PRODUCT_ID), []);
    const make = factory();
    const { result } = renderHook(
      () => useProductEvents(SEED_PRODUCT_ID, { eventSourceFactory: make }),
      { wrapper: wrapper(client) },
    );

    act(() => fake.emit('release.cut', { release: NEW_RELEASE }));

    expect(result.current.lastReleaseId).toBe('rel-1');
    const releases = client.getQueryData<readonly Release[]>(queryKeys.releases(SEED_PRODUCT_ID));
    expect(releases).toHaveLength(1);
    expect(releases?.[0]?.id).toBe('rel-1');
  });

  it('toggles connected on open and error', () => {
    const make = factory();
    const { result } = renderHook(
      () => useProductEvents(SEED_PRODUCT_ID, { eventSourceFactory: make }),
      { wrapper: wrapper(client) },
    );

    act(() => fake.emit('open'));
    expect(result.current.connected).toBe(true);

    act(() => fake.emit('error'));
    expect(result.current.connected).toBe(false);
  });

  it('closes the underlying source on unmount', () => {
    const make = factory();
    const { unmount } = renderHook(
      () => useProductEvents(SEED_PRODUCT_ID, { eventSourceFactory: make }),
      { wrapper: wrapper(client) },
    );

    expect(fake.closed).toBe(false);
    unmount();
    expect(fake.closed).toBe(true);
  });
});
