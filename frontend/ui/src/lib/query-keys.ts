// Central query-cache keys. Foundation owns these so every lane invalidates/reads the
// same entries (R3's SSE handlers and R2's cut mutation both target these exact keys).

export const queryKeys = {
  meta: ['meta'] as const,
  me: ['auth', 'me'] as const,
  products: ['products'] as const,
  product: (productId: string) => ['products', productId] as const,
  timeline: (productId: string) => ['products', productId, 'timeline'] as const,
  releases: (productId: string) => ['products', productId, 'releases'] as const,
  release: (releaseId: string) => ['releases', releaseId] as const,
  components: (productId: string) => ['products', productId, 'components'] as const,
  graph: (productId: string) => ['products', productId, 'graph'] as const,
  impact: (productId: string, componentId: string) =>
    ['products', productId, 'impact', componentId] as const,
  versions: (componentId: string) => ['components', componentId, 'versions'] as const,
} as const;
