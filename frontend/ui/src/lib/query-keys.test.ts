import { describe, expect, it } from 'vitest';

import { queryKeys } from './query-keys';

describe('queryKeys', () => {
  it('produces stable, scoped keys for every resource', () => {
    expect(queryKeys.meta).toEqual(['meta']);
    expect(queryKeys.me).toEqual(['auth', 'me']);
    expect(queryKeys.products).toEqual(['products']);
    expect(queryKeys.product('p')).toEqual(['products', 'p']);
    expect(queryKeys.timeline('p')).toEqual(['products', 'p', 'timeline']);
    expect(queryKeys.releases('p')).toEqual(['products', 'p', 'releases']);
    expect(queryKeys.release('r')).toEqual(['releases', 'r']);
    expect(queryKeys.components('p')).toEqual(['products', 'p', 'components']);
    expect(queryKeys.versions('c')).toEqual(['components', 'c', 'versions']);
    expect(queryKeys.graph('p')).toEqual(['products', 'p', 'graph']);
    expect(queryKeys.impact('p', 'c')).toEqual(['products', 'p', 'impact', 'c']);
  });
});
