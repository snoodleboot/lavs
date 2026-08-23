import { useCallback, useRef, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react';

import { hueForIndex } from '@/lib';
import type { Dependency, Timeline } from '@/types';

import { DependencyEdges } from './dependency-edges';
import {
  LABEL_ANCHOR_X,
  LANE_TOP,
  VIEWBOX,
  labelWidth,
  tOfX,
  xOf,
  yOf,
  type TimeAxis,
} from './geometry';
import { Meridian } from './meridian';
import { deriveManifest } from './projection';
import { Stream } from './stream';
import styles from './constellation-view.module.css';

const EMPTY_IDS: ReadonlySet<string> = new Set<string>();
const EMPTY_DEPENDENCIES: readonly Dependency[] = [];

/** Presentational SVG for the Constellation: streams, stations, meridian, connectors. */
export interface ConstellationViewProps {
  readonly timeline: Timeline;
  readonly axis: TimeAxis;
  readonly position: number;
  readonly onPositionChange: (tick: number) => void;
  readonly freshVersionIds?: ReadonlySet<string>;
  readonly rolledBackVersionIds?: ReadonlySet<string>;
  /** P9 dependency edges from `GET /products/{id}/graph` — decorative, drawn under the streams. */
  readonly dependencies?: readonly Dependency[];
}

export function ConstellationView(props: ConstellationViewProps): ReactNode {
  const {
    timeline,
    axis,
    position,
    onPositionChange,
    freshVersionIds = EMPTY_IDS,
    rolledBackVersionIds = EMPTY_IDS,
    dependencies = EMPTY_DEPENDENCIES,
  } = props;

  const { maxTick } = axis;
  const svgRef = useRef<SVGSVGElement>(null);
  const draggingRef = useRef<boolean>(false);

  const tick = Math.floor(position + 1e-6);
  const laneCount = timeline.components.length;
  const meridianX = xOf(position, maxTick);

  const manifest = deriveManifest(timeline, axis, tick);
  const pinnedByComponent = new Map<string, string | null>(
    manifest.map((entry) => [entry.component.id, entry.version?.id ?? null]),
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<SVGGElement>): void => {
      let next: number | null = null;
      if (event.key === 'ArrowRight') next = Math.min(maxTick, Math.floor(position) + 1);
      else if (event.key === 'ArrowLeft') next = Math.max(0, Math.ceil(position) - 1);
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = maxTick;

      if (next !== null) {
        event.preventDefault();
        onPositionChange(next);
      }
    },
    [maxTick, position, onPositionChange],
  );

  const scrubToClientX = useCallback(
    (clientX: number): void => {
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      if (rect.width === 0) return;
      const vx = ((clientX - rect.left) / rect.width) * VIEWBOX.width;
      // Half-tick snap for smooth dragging (mirrors the mockup).
      const snapped = Math.round(tOfX(vx, maxTick) * 2) / 2;
      onPositionChange(snapped);
    },
    [maxTick, onPositionChange],
  );

  const handlePointerDown = useCallback(
    (event: PointerEvent<SVGSVGElement>): void => {
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      if (rect.width === 0) return;
      const vx = ((event.clientX - rect.left) / rect.width) * VIEWBOX.width;
      // Only grab when the pointer lands near the meridian line/handle.
      if (Math.abs(vx - xOf(position, maxTick)) < 28) {
        draggingRef.current = true;
        svg.setPointerCapture?.(event.pointerId);
        scrubToClientX(event.clientX);
      }
    },
    [maxTick, position, scrubToClientX],
  );

  const handlePointerMove = useCallback(
    (event: PointerEvent<SVGSVGElement>): void => {
      if (draggingRef.current) scrubToClientX(event.clientX);
    },
    [scrubToClientX],
  );

  const handlePointerUp = useCallback((): void => {
    draggingRef.current = false;
  }, []);

  return (
    <svg
      ref={svgRef}
      className={styles.stage}
      viewBox={`0 0 ${VIEWBOX.width} ${VIEWBOX.height}`}
      preserveAspectRatio="xMidYMid meet"
      role="group"
      aria-label={`Constellation for ${timeline.product.name}`}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      {timeline.components.map((component, index) => {
        const y = yOf(index, laneCount);
        const hue = hueForIndex(index);
        return (
          <g key={`lane-${component.id}`}>
            <line
              x1={VIEWBOX.padLeft}
              y1={y}
              x2={VIEWBOX.width - VIEWBOX.padRight}
              y2={y}
              className={styles.laneBase}
            />
            <text
              x={LABEL_ANCHOR_X}
              y={y + 4}
              textAnchor="end"
              textLength={labelWidth(component.name)}
              lengthAdjust="spacing"
              className={styles.laneLabel}
              style={{ fill: hue }}
            >
              {component.name}
            </text>
          </g>
        );
      })}

      <text
        x={xOf(maxTick, maxTick)}
        y={LANE_TOP - 18}
        textAnchor="middle"
        className={styles.nowLabel}
      >
        now
      </text>

      <DependencyEdges dependencies={dependencies} components={timeline.components} />

      {timeline.components.map((component, index) => (
        <Stream
          key={component.id}
          component={component}
          laneIndex={index}
          laneCount={laneCount}
          axis={axis}
          tick={tick}
          hue={hueForIndex(index)}
          pinnedVersionId={pinnedByComponent.get(component.id) ?? null}
          meridianX={meridianX}
          freshVersionIds={freshVersionIds}
          rolledBackVersionIds={rolledBackVersionIds}
        />
      ))}

      <Meridian x={meridianX} position={position} maxTick={maxTick} onKeyDown={handleKeyDown} />
    </svg>
  );
}
