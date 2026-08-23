import type { ReactNode } from 'react';

import { formatVersion } from '@/lib';
import type { ChangeLevel, ComponentWithVersions } from '@/types';

import { xOf, yOf, type TimeAxis } from './geometry';
import { Station, type ImpactState } from './station';
import styles from './constellation-view.module.css';

/** A component's horizontal timeline: its stream line, stations and pinned connector. */
export interface StreamProps {
  readonly component: ComponentWithVersions;
  readonly laneIndex: number;
  readonly laneCount: number;
  readonly axis: TimeAxis;
  readonly tick: number;
  readonly hue: string;
  readonly pinnedVersionId: string | null;
  readonly meridianX: number;
  readonly freshVersionIds: ReadonlySet<string>;
  readonly rolledBackVersionIds: ReadonlySet<string>;
  /** P9 impact state for this lane — applied to the pinned station only. */
  readonly impactState?: ImpactState;
  /** P9 projected change level for this lane — applied to the pinned station only. */
  readonly impactLevel?: ChangeLevel | null;
  /** P9 change level of the PINNED version in the latest cut release. */
  readonly changeLevel?: ChangeLevel | null;
  /** JS seam for `prefers-reduced-motion`. */
  readonly animated?: boolean;
}

export function Stream(props: StreamProps): ReactNode {
  const {
    component,
    laneIndex,
    laneCount,
    axis,
    tick,
    hue,
    pinnedVersionId,
    meridianX,
    freshVersionIds,
    rolledBackVersionIds,
    impactState,
    impactLevel = null,
    changeLevel = null,
    animated = false,
  } = props;

  const y = yOf(laneIndex, laneCount);
  const { maxTick } = axis;
  const ticks = component.versions.map((version) => axis.tickOf(version.id));
  const firstX = xOf(Math.min(...ticks), maxTick);
  const lastX = xOf(Math.max(...ticks), maxTick);
  const pinnedX = pinnedVersionId ? xOf(axis.tickOf(pinnedVersionId), maxTick) : null;

  return (
    <g data-testid={`stream-${component.id}`} aria-label={component.name}>
      <line
        x1={firstX}
        y1={y}
        x2={lastX}
        y2={y}
        className={styles.streamLine}
        style={{ stroke: hue }}
      />

      {pinnedX !== null ? (
        <g className={styles.connector} data-testid={`connector-${component.id}`}>
          <line
            x1={pinnedX}
            y1={y}
            x2={meridianX}
            y2={y}
            className={styles.connectorLine}
            style={{ stroke: hue }}
          />
          <circle
            cx={meridianX}
            cy={y}
            r={3}
            className={styles.connectorDot}
            style={{ fill: hue }}
          />
        </g>
      ) : null}

      {component.versions.map((version) => {
        const versionTick = axis.tickOf(version.id);
        // Release-frozen and impact state are version-scoped: only the station the meridian
        // pins carries them, so scrubbing never smears a badge across history.
        const isPinned = version.id === pinnedVersionId;
        return (
          <Station
            key={version.id}
            versionId={version.id}
            label={formatVersion(version)}
            cx={xOf(versionTick, maxTick)}
            cy={y}
            hue={hue}
            pinned={isPinned}
            reached={versionTick <= tick}
            fresh={freshVersionIds.has(version.id)}
            rolledBack={rolledBackVersionIds.has(version.id)}
            impactState={isPinned ? impactState : undefined}
            impactLevel={isPinned ? impactLevel : null}
            changeLevel={isPinned ? changeLevel : null}
            animated={animated}
          />
        );
      })}
    </g>
  );
}
