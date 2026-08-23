import type { GraphResponse, Result } from '@/types';

import { http } from './http';

/** The product's intra-product dependency DAG — contract §10. Read-only in this scope. */
export function getGraph(productId: string, signal?: AbortSignal): Promise<Result<GraphResponse>> {
  return http.get<GraphResponse>(`/products/${productId}/graph`, { signal });
}
