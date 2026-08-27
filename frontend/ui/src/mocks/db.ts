import type { ComponentWithVersions, Dependency, Principal, Product, Release } from '@/types';

import {
  seedComponents,
  seedDependencies,
  seedPrincipal,
  seedProduct,
  seedReleases,
} from './fixtures';

// Mutable in-memory store backing the MSW handlers. Tests mutate it (e.g. cut a release)
// and reset it between cases via resetDb() (wired in vitest.setup.ts).

export interface MockDb {
  product: Product;
  components: ComponentWithVersions[];
  dependencies: Dependency[];
  releases: Release[];
  principal: Principal | null;
  releaseCounter: number;
}

function freshDb(): MockDb {
  return {
    product: seedProduct(),
    components: seedComponents(),
    dependencies: seedDependencies(),
    releases: seedReleases(),
    // Default to authenticated so component tests render the app; login tests override.
    principal: seedPrincipal,
    releaseCounter: 0,
  };
}

export let db: MockDb = freshDb();

export function resetDb(): void {
  db = freshDb();
}
