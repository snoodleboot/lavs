import { describe, expect, it } from 'vitest';

import { SEED_BUMP_RATIONALE } from '@/mocks';

import { formatBumpRationale } from './bump-rationale';

describe('formatBumpRationale', () => {
  it('summarises the shipped JSON shape as one human line', () => {
    // The seed has 4 components, one of which has own === 'none'.
    expect(formatBumpRationale(SEED_BUMP_RATIONALE)).toBe('3 of 4 components changed.');
  });

  it('calls out a removal, which forces a major', () => {
    const raw = JSON.stringify({
      policy: 'default',
      product_bump: 'major',
      removed_any: true,
      components: { 'comp-api': { own: 'minor', effective: 'minor' } },
    });

    expect(formatBumpRationale(raw)).toBe(
      '1 of 1 component changed; a removed component forces a major.',
    );
  });

  it('prefers a ready-made human line if the backend ever ships one', () => {
    expect(formatBumpRationale('{"reason":"  api minor propagated to ui  "}')).toBe(
      'api minor propagated to ui',
    );
  });

  it('falls back to the raw string when the JSON is malformed', () => {
    expect(formatBumpRationale('  not json at all  ')).toBe('not json at all');
  });

  it('falls back to the raw string for an unrecognised shape', () => {
    expect(formatBumpRationale('{"policy":"default"}')).toBe('{"policy":"default"}');
    expect(formatBumpRationale('{"components":{}}')).toBe('{"components":{}}');
    expect(formatBumpRationale('42')).toBe('42');
  });

  it('returns null for null, undefined and blank input', () => {
    expect(formatBumpRationale(null)).toBeNull();
    expect(formatBumpRationale(undefined)).toBeNull();
    expect(formatBumpRationale('   ')).toBeNull();
  });
});
