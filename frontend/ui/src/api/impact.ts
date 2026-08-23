import type { Impact, Result } from '@/types';

import { http } from './http';

/** Transitive dependents a hypothetical major change to `componentId` would touch (§10). */
export function getImpact(
  productId: string,
  componentId: string,
  signal?: AbortSignal,
): Promise<Result<Impact>> {
  const query = `?component=${encodeURIComponent(componentId)}`;
  return http.get<Impact>(`/products/${productId}/impact${query}`, { signal });
}
