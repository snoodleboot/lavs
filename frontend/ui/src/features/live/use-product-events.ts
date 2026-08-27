import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';

import { subscribeToProductEvents } from '@/api';
import { queryKeys } from '@/lib';
import type { GraphResponse, Release, Timeline } from '@/types';

import {
  applyDependencyAdded,
  applyDependencyRemoved,
  applyVersionCreated,
  applyVersionRolledBack,
} from './event-cache';
import { useReducedMotion } from './use-reduced-motion';

// How long a freshly-created version keeps its transient "pulse" flag before it clears.
const PULSE_DURATION_MS = 1600;

export interface LiveState {
  /** Versions created since mount that are still pulsing (transient). */
  readonly freshVersionIds: ReadonlySet<string>;
  /** Versions rolled back since mount (dim/strike in the view). */
  readonly rolledBackVersionIds: ReadonlySet<string>;
  /** Id of the most recently cut release, or null. */
  readonly lastReleaseId: string | null;
  /** Whether the SSE connection is currently open. */
  readonly connected: boolean;
}

export interface UseProductEventsOptions {
  /** Injectable EventSource factory for tests. */
  readonly eventSourceFactory?: (url: string) => EventSource;
}

/**
 * Bridge the live SSE stream into the TanStack Query cache plus transient visual state.
 * Applies pure reducers optimistically, then invalidates to reconcile with the server.
 * A no-op while `productId` is undefined. Cleans up the subscription and all timers on
 * unmount or `productId` change.
 */
export function useProductEvents(
  productId: string | undefined,
  options: UseProductEventsOptions = {},
): LiveState {
  const queryClient = useQueryClient();
  const reducedMotion = useReducedMotion();

  const [freshVersionIds, setFreshVersionIds] = useState<ReadonlySet<string>>(() => new Set());
  const [rolledBackVersionIds, setRolledBackVersionIds] = useState<ReadonlySet<string>>(
    () => new Set(),
  );
  const [lastReleaseId, setLastReleaseId] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean>(false);

  // Keep mutable references so the (once-per-productId) subscription reads fresh values.
  const reducedMotionRef = useRef<boolean>(reducedMotion);
  reducedMotionRef.current = reducedMotion;

  const factoryRef = useRef<UseProductEventsOptions['eventSourceFactory']>(
    options.eventSourceFactory,
  );
  factoryRef.current = options.eventSourceFactory;

  const pulseTimers = useRef<Set<ReturnType<typeof setTimeout>>>(new Set());

  const scheduleFreshRemoval = useCallback((versionId: string): void => {
    const delay = reducedMotionRef.current ? 0 : PULSE_DURATION_MS;
    const timer = setTimeout(() => {
      pulseTimers.current.delete(timer);
      setFreshVersionIds((prev) => {
        if (!prev.has(versionId)) return prev;
        const next = new Set(prev);
        next.delete(versionId);
        return next;
      });
    }, delay);
    pulseTimers.current.add(timer);
  }, []);

  useEffect(() => {
    if (!productId) return;

    const timelineKey = queryKeys.timeline(productId);
    const releasesKey = queryKeys.releases(productId);
    const graphKey = queryKeys.graph(productId);

    const dispose = subscribeToProductEvents(
      productId,
      {
        onOpen: () => setConnected(true),
        onError: () => setConnected(false),
        onVersionCreated: (event) => {
          queryClient.setQueryData<Timeline>(timelineKey, (prev) =>
            prev ? applyVersionCreated(prev, event) : prev,
          );
          setFreshVersionIds((prev) => new Set(prev).add(event.version.id));
          void queryClient.invalidateQueries({ queryKey: timelineKey });
          scheduleFreshRemoval(event.version.id);
        },
        onVersionRolledBack: (event) => {
          queryClient.setQueryData<Timeline>(timelineKey, (prev) =>
            prev ? applyVersionRolledBack(prev, event) : prev,
          );
          setRolledBackVersionIds((prev) => new Set(prev).add(event.version_id));
          void queryClient.invalidateQueries({ queryKey: timelineKey });
        },
        onDependencyAdded: (event) => {
          queryClient.setQueryData<GraphResponse>(graphKey, (prev) =>
            prev ? applyDependencyAdded(prev, event) : prev,
          );
          void queryClient.invalidateQueries({ queryKey: graphKey });
        },
        onDependencyRemoved: (event) => {
          queryClient.setQueryData<GraphResponse>(graphKey, (prev) =>
            prev ? applyDependencyRemoved(prev, event) : prev,
          );
          void queryClient.invalidateQueries({ queryKey: graphKey });
        },
        onReleaseCut: (event) => {
          setLastReleaseId(event.release.id);
          queryClient.setQueryData<readonly Release[]>(releasesKey, (prev) =>
            prev ? [event.release, ...prev] : prev,
          );
          void queryClient.invalidateQueries({ queryKey: releasesKey });
        },
      },
      { eventSourceFactory: factoryRef.current },
    );

    const timers = pulseTimers.current;
    return (): void => {
      dispose();
      timers.forEach((timer) => clearTimeout(timer));
      timers.clear();
    };
  }, [productId, queryClient, scheduleFreshRemoval]);

  return { freshVersionIds, rolledBackVersionIds, lastReleaseId, connected };
}
