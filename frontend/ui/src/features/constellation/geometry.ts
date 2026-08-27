import type { Timeline } from '@/types';

/**
 * The ordinal "release tick" axis (decision G-P5d). Every version's `created_at`
 * across all components is collected, sorted ascending, and each DISTINCT timestamp
 * is assigned a global ordinal tick `0..maxTick`. This replaces the mockup's
 * hard-coded `t` values with ticks derived from the real timeline.
 */
export interface TimeAxis {
  /** The highest tick (== count of distinct timestamps minus one, floored at 0). */
  readonly maxTick: number;
  /** Ordinal tick for a version id, or `-1` if the id is unknown to this axis. */
  readonly tickOf: (versionId: string) => number;
}

/** viewBox layout — mirrors the mockup's VBW/VBH/PADL/PADR/PADT/PADB constants. */
export const VIEWBOX = {
  width: 900,
  height: 460,
  padLeft: 120,
  padRight: 70,
  padTop: 46,
  padBottom: 46,
} as const;

/** Top of the first lane, leaving room for the "now" marker and station labels. */
export const LANE_TOP = VIEWBOX.padTop + 18;

/**
 * The left gutter is split into two reserved bands so the P9 dependency arcs never cross a
 * lane-label glyph: the label column `[LABEL_COLUMN_LEFT, LABEL_ANCHOR_X]` and, left of it,
 * the arc gutter `[LABEL_COLUMN_LEFT - GUTTER_DEPTH, LABEL_COLUMN_LEFT]`.
 */

/** Lane labels are end-anchored here; their glyphs extend leftward from this x. */
export const LABEL_ANCHOR_X = VIEWBOX.padLeft - 16;

/** Nominal advance width of one lane-label glyph (13px / weight 600 sans). */
export const LABEL_CHAR_WIDTH = 7.2;

/** Hard cap on a lane label's rendered width — the column never grows past this. */
export const LABEL_MAX_WIDTH = 76;

/** Left edge of the label column, i.e. the right edge of the dependency-arc gutter. */
export const LABEL_COLUMN_LEFT = LABEL_ANCHOR_X - LABEL_MAX_WIDTH;

/** How far left of the label column a dependency arc may bow. */
export const GUTTER_DEPTH = 24;

/**
 * Vertical offset of a station's level badge (P9 impact / change_level). It sits *below* the
 * dot because the `cy - 13` slot above already carries the version label.
 */
export const BADGE_DY = 20;

/**
 * The exact width a lane label is rendered at (via SVG `textLength`), bounded by
 * `LABEL_MAX_WIDTH`. Deriving it from the name length keeps the guarantee "no glyph left of
 * `LABEL_COLUMN_LEFT`" deterministic and testable, which a CSS width cap cannot be on SVG text.
 */
export function labelWidth(name: string): number {
  return Math.min(LABEL_MAX_WIDTH, Math.max(1, name.length) * LABEL_CHAR_WIDTH);
}

/** Vertical space allotted to a single component lane. */
export function laneHeight(laneCount: number): number {
  const usable = VIEWBOX.height - LANE_TOP - VIEWBOX.padBottom;
  return usable / Math.max(1, laneCount);
}

/** Map an ordinal tick to an x coordinate in viewBox space. */
export function xOf(tick: number, maxTick: number): number {
  const span = VIEWBOX.width - VIEWBOX.padLeft - VIEWBOX.padRight;
  const denom = maxTick <= 0 ? 1 : maxTick;
  return VIEWBOX.padLeft + (tick / denom) * span;
}

/** Inverse of `xOf`: map an x coordinate back to a (clamped) fractional tick. */
export function tOfX(x: number, maxTick: number): number {
  const span = VIEWBOX.width - VIEWBOX.padLeft - VIEWBOX.padRight;
  const denom = maxTick <= 0 ? 1 : maxTick;
  const raw = ((x - VIEWBOX.padLeft) / span) * denom;
  return Math.max(0, Math.min(maxTick, raw));
}

/** Vertical center of a component lane by its index. */
export function yOf(laneIndex: number, laneCount: number): number {
  const height = laneHeight(laneCount);
  return LANE_TOP + height * laneIndex + height * 0.5;
}

interface AxisEntry {
  readonly versionId: string;
  readonly time: number;
}

/** Build the ordinal release-tick axis from a timeline (decision G-P5d). */
export function buildTimeAxis(timeline: Timeline): TimeAxis {
  const entries: AxisEntry[] = [];
  const distinctTimes = new Set<number>();

  for (const component of timeline.components) {
    for (const version of component.versions) {
      const time = Date.parse(version.created_at);
      entries.push({ versionId: version.id, time });
      distinctTimes.add(time);
    }
  }

  const sortedTimes = [...distinctTimes].sort((a, b) => a - b);
  const tickByTime = new Map<number, number>();
  sortedTimes.forEach((time, index) => tickByTime.set(time, index));

  const tickByVersion = new Map<string, number>();
  for (const entry of entries) {
    tickByVersion.set(entry.versionId, tickByTime.get(entry.time) ?? -1);
  }

  const maxTick = Math.max(0, sortedTimes.length - 1);

  return {
    maxTick,
    tickOf: (versionId: string): number => tickByVersion.get(versionId) ?? -1,
  };
}
