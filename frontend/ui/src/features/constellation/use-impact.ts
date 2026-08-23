import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { getImpact } from '@/api';
import { queryKeys, unwrap } from '@/lib';
import type { Impact } from '@/types';

/** Hovering must not re-fetch a blast radius that cannot change while a selection is held. */
const IMPACT_STALE_TIME_MS = 30_000;

/** The blast radius of a hypothetical major change to `componentId` (contract §10). */
export function useImpact(
  productId: string | undefined,
  componentId: string | null | undefined,
): UseQueryResult<Impact> {
  return useQuery({
    queryKey: queryKeys.impact(productId ?? 'none', componentId ?? 'none'),
    queryFn: ({ signal }) => unwrap(getImpact(productId ?? '', componentId ?? '', signal)),
    // Fires only once a component is actually selected.
    enabled: Boolean(productId && componentId),
    staleTime: IMPACT_STALE_TIME_MS,
  });
}
