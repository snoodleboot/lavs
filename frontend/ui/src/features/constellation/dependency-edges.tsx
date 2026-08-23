import type { ReactNode } from 'react';

import type { Component, Dependency } from '@/types';

import { GUTTER_DEPTH, LABEL_COLUMN_LEFT, yOf } from './geometry';
import styles from './constellation-view.module.css';

/** Half-height of the arrowhead drawn at the dependency (the `to`) endpoint. */
const ARROW_HALF = 4;
/** How far the arrowhead reaches back along the arc from its tip. */
const ARROW_LENGTH = 6;

/** The quiet left-gutter "spine": one arc per dependency, `from` → `to`. */
export interface DependencyEdgesProps {
  readonly dependencies: readonly Dependency[];
  /** Authoritative lane order — the timeline's components, never the graph's nodes. */
  readonly components: readonly Component[];
}

interface Arc {
  readonly id: string;
  readonly path: string;
  readonly arrow: string;
}

function arcFor(fromY: number, toY: number): { path: string; arrow: string } {
  const depth = 12 + Math.min(36, Math.abs(fromY - toY) * 0.25);
  const controlX = Math.max(LABEL_COLUMN_LEFT - GUTTER_DEPTH, LABEL_COLUMN_LEFT - depth);
  const path = `M ${LABEL_COLUMN_LEFT} ${fromY} Q ${controlX} ${(fromY + toY) / 2} ${LABEL_COLUMN_LEFT} ${toY}`;
  // Head at the dependency, pointing rightward toward its lane label.
  const backX = LABEL_COLUMN_LEFT - ARROW_LENGTH;
  const arrow = `M ${LABEL_COLUMN_LEFT} ${toY} L ${backX} ${toY - ARROW_HALF} L ${backX} ${toY + ARROW_HALF} Z`;
  return { path, arrow };
}

export function DependencyEdges({ dependencies, components }: DependencyEdgesProps): ReactNode {
  const laneCount = components.length;
  const indexOf = new Map(components.map((component, index) => [component.id, index]));

  const arcs: Arc[] = [];
  for (const dependency of dependencies) {
    const fromIndex = indexOf.get(dependency.from_component_id);
    const toIndex = indexOf.get(dependency.to_component_id);
    // Defensive: the graph can name a component the timeline has not loaded — skip it.
    if (fromIndex === undefined || toIndex === undefined) continue;
    const { path, arrow } = arcFor(yOf(fromIndex, laneCount), yOf(toIndex, laneCount));
    arcs.push({ id: dependency.id, path, arrow });
  }

  return (
    <g data-testid="dependency-edges" className={styles.edgeLayer} aria-hidden="true">
      {arcs.map((arc) => (
        <g key={arc.id} className={styles.dependencyEdge}>
          <path d={arc.path} data-testid={`dependency-edge-${arc.id}`} className={styles.edgeArc} />
          <path
            d={arc.arrow}
            data-testid={`dependency-arrow-${arc.id}`}
            className={styles.edgeArrow}
          />
        </g>
      ))}
    </g>
  );
}
