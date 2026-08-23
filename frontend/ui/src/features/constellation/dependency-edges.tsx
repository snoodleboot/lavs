import type { ReactNode } from 'react';

import type { ChangeLevel, Component, Dependency } from '@/types';

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
  /** P9 impact source; `null`/absent means nothing is selected and no edge is brightened. */
  readonly selectedComponentId?: string | null;
  /** P9 blast radius, keyed by component id. */
  readonly impactedByComponent?: ReadonlyMap<string, ChangeLevel>;
}

interface Arc {
  readonly id: string;
  readonly path: string;
  readonly arrow: string;
  readonly active: boolean;
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

export function DependencyEdges(props: DependencyEdgesProps): ReactNode {
  const { dependencies, components, selectedComponentId = null, impactedByComponent } = props;

  const laneCount = components.length;
  const indexOf = new Map(components.map((component, index) => [component.id, index]));

  // An edge lights up only when BOTH ends are in the blast radius. An edge leaving the source
  // toward one of its own dependencies has an unaffected far end, so it stays muted.
  const inRadius = (componentId: string): boolean =>
    componentId === selectedComponentId || Boolean(impactedByComponent?.has(componentId));

  const arcs: Arc[] = [];
  for (const dependency of dependencies) {
    const fromIndex = indexOf.get(dependency.from_component_id);
    const toIndex = indexOf.get(dependency.to_component_id);
    // Defensive: the graph can name a component the timeline has not loaded — skip it.
    if (fromIndex === undefined || toIndex === undefined) continue;
    const { path, arrow } = arcFor(yOf(fromIndex, laneCount), yOf(toIndex, laneCount));
    const active =
      selectedComponentId !== null &&
      inRadius(dependency.from_component_id) &&
      inRadius(dependency.to_component_id);
    arcs.push({ id: dependency.id, path, arrow, active });
  }

  return (
    <g data-testid="dependency-edges" className={styles.edgeLayer} aria-hidden="true">
      {arcs.map((arc) => (
        <g
          key={arc.id}
          className={`${styles.dependencyEdge} ${arc.active ? styles.dependencyEdgeActive : ''}`}
          data-active={arc.active}
        >
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
