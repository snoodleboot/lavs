import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { getGraph } from '@/api';
import { queryKeys, unwrap } from '@/lib';
import type { GraphResponse } from '@/types';

/** The product's dependency DAG (contract §10). REST is the source of truth for the edges. */
export function useGraph(productId: string | undefined): UseQueryResult<GraphResponse> {
  return useQuery({
    queryKey: productId ? queryKeys.graph(productId) : queryKeys.graph('none'),
    queryFn: ({ signal }) => unwrap(getGraph(productId ?? '', signal)),
    enabled: Boolean(productId),
  });
}
