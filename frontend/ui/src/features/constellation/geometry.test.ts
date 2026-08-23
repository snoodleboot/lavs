import { describe, expect, it } from 'vitest';

import { seedComponents, seedProduct } from '@/mocks';
import type { Timeline } from '@/types';

import {
  GUTTER_DEPTH,
  LABEL_ANCHOR_X,
  LABEL_CHAR_WIDTH,
  LABEL_COLUMN_LEFT,
  LABEL_MAX_WIDTH,
  LANE_TOP,
  VIEWBOX,
  buildTimeAxis,
  labelWidth,
  tOfX,
  xOf,
  yOf,
} from './geometry';

function makeTimeline(): Timeline {
  return { product: seedProduct(), components: seedComponents() };
}

describe('buildTimeAxis', () => {
  it('assigns one ordinal tick per distinct timestamp (12 days → maxTick 11)', () => {
    const axis = buildTimeAxis(makeTimeline());

    // Seed spans 12 distinct days (2026-05-01..12).
    expect(axis.maxTick).toBe(11);
  });

  it('orders ticks ascending by created_at and shares ticks across components', () => {
    const axis = buildTimeAxis(makeTimeline());

    // Earliest stations (day 1) share tick 0.
    expect(axis.tickOf('comp-api-v0')).toBe(0);
    expect(axis.tickOf('comp-helm-v0')).toBe(0);
    // day 2 → tick 1, day 3 → tick 2 (shared api + cli).
    expect(axis.tickOf('comp-ui-v0')).toBe(1);
    expect(axis.tickOf('comp-api-v1')).toBe(2);
    expect(axis.tickOf('comp-cli-v0')).toBe(2);
    // Latest station (day 12) → tick 11.
    expect(axis.tickOf('comp-ui-v4')).toBe(11);
  });

  it('returns a strictly increasing tick per version within a component', () => {
    const axis = buildTimeAxis(makeTimeline());
    const apiTicks = [
      'comp-api-v0',
      'comp-api-v1',
      'comp-api-v2',
      'comp-api-v3',
      'comp-api-v4',
    ].map((id) => axis.tickOf(id));

    for (let i = 1; i < apiTicks.length; i += 1) {
      expect(apiTicks[i]).toBeGreaterThan(apiTicks[i - 1]!);
    }
  });

  it('returns -1 for an unknown version id', () => {
    const axis = buildTimeAxis(makeTimeline());

    expect(axis.tickOf('nope')).toBe(-1);
  });

  it('clamps maxTick to 0 for an empty timeline', () => {
    const axis = buildTimeAxis({ product: seedProduct(), components: [] });

    expect(axis.maxTick).toBe(0);
  });
});

describe('coordinate helpers', () => {
  it('xOf is monotonic and anchored to the padded canvas', () => {
    expect(xOf(0, 11)).toBe(VIEWBOX.padLeft);
    expect(xOf(11, 11)).toBe(VIEWBOX.width - VIEWBOX.padRight);
    expect(xOf(3, 11)).toBeGreaterThan(xOf(0, 11));
    expect(xOf(11, 11)).toBeGreaterThan(xOf(3, 11));
  });

  it('tOfX inverts xOf and clamps to the range', () => {
    expect(tOfX(xOf(4, 11), 11)).toBeCloseTo(4, 6);
    expect(tOfX(-9999, 11)).toBe(0);
    expect(tOfX(9999, 11)).toBe(11);
  });

  it('guards against a zero span (single-timestamp axis)', () => {
    expect(xOf(0, 0)).toBe(VIEWBOX.padLeft);
    expect(tOfX(500, 0)).toBe(0);
  });

  it('yOf spaces lanes monotonically below the lane top', () => {
    const y0 = yOf(0, 4);
    const y1 = yOf(1, 4);
    const y3 = yOf(3, 4);

    expect(y0).toBeGreaterThan(LANE_TOP);
    expect(y1).toBeGreaterThan(y0);
    expect(y3).toBeGreaterThan(y1);
  });
});

describe('the reserved left gutter', () => {
  it('places the label column left of the lane start and the arc gutter left of that', () => {
    expect(LABEL_ANCHOR_X).toBeLessThan(VIEWBOX.padLeft);
    expect(LABEL_COLUMN_LEFT).toBe(LABEL_ANCHOR_X - LABEL_MAX_WIDTH);
    expect(LABEL_COLUMN_LEFT - GUTTER_DEPTH).toBeGreaterThan(0);
  });
});

describe('labelWidth', () => {
  it('scales with the name length until the column cap', () => {
    expect(labelWidth('ab')).toBeCloseTo(2 * LABEL_CHAR_WIDTH);
    expect(labelWidth('a-very-long-component-name')).toBe(LABEL_MAX_WIDTH);
  });

  it('never returns zero for an empty name', () => {
    expect(labelWidth('')).toBeCloseTo(LABEL_CHAR_WIDTH);
  });
});
