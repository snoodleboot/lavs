import type { ReactNode } from 'react';

import type { ChangeLevel } from '@/types';

import { BADGE_DY } from './geometry';
import styles from './constellation-view.module.css';

/** How a station relates to the currently selected component's blast radius. */
export type ImpactState = 'source' | 'impacted' | 'dimmed';

const LEVEL_CLASS: Readonly<Record<ChangeLevel, string>> = {
  // `noUncheckedIndexedAccess` widens CSS-module lookups to `string | undefined`.
  major: styles.levelMajor ?? '',
  minor: styles.levelMinor ?? '',
  patch: styles.levelPatch ?? '',
};

/** A single version node on a component stream. */
export interface StationProps {
  readonly versionId: string;
  readonly label: string;
  readonly cx: number;
  readonly cy: number;
  readonly hue: string;
  /** Pinned by the current meridian (enlarged + glowing). */
  readonly pinned: boolean;
  /** The meridian has reached this station (else dimmed as "not yet"). */
  readonly reached: boolean;
  /** Freshly created — pulse for emphasis (collapsed under reduced-motion). */
  readonly fresh: boolean;
  /** Rolled back — dimmed + struck through. */
  readonly rolledBack: boolean;
  /** P9 impact highlight; `undefined` means no component is selected. */
  readonly impactState?: ImpactState;
  /** P9 projected change level for an impacted station. */
  readonly impactLevel?: ChangeLevel | null;
  /** P9 own change level of THIS version in the latest cut release. */
  readonly changeLevel?: ChangeLevel | null;
  /** JS seam for `prefers-reduced-motion`: gates the impact glow. */
  readonly animated?: boolean;
}

export function Station(props: StationProps): ReactNode {
  const {
    versionId,
    label,
    cx,
    cy,
    hue,
    pinned,
    reached,
    fresh,
    rolledBack,
    impactState,
    impactLevel = null,
    changeLevel = null,
    animated = false,
  } = props;

  // While a selection is active every station carries an impact state, and the impact badge
  // owns the badge slot — the change-level badge yields to it.
  const selectionActive = impactState !== undefined;
  const badgeLevel = impactLevel ?? (selectionActive ? null : changeLevel);
  const showsChangeLevel = badgeLevel !== null && impactLevel === null;

  const radius = pinned ? 8 : 5.5;
  const className = [
    styles.station,
    pinned ? styles.stationPinned : '',
    reached ? '' : styles.stationUnreached,
    fresh ? styles.stationFresh : '',
    rolledBack ? styles.stationRolledBack : '',
    impactState === 'source' ? styles.stationSource : '',
    impactState === 'impacted' ? styles.stationImpacted : '',
    impactState === 'dimmed' ? styles.stationDimmed : '',
    animated && (impactState === 'source' || impactState === 'impacted') ? styles.animated : '',
  ]
    .filter(Boolean)
    .join(' ');

  const impactSuffix =
    impactState === 'source' ? ' (source)' : impactLevel ? ` (impact: ${impactLevel})` : '';
  const changeSuffix = showsChangeLevel ? ` (change: ${badgeLevel})` : '';
  const ariaLabel =
    `${label}${pinned ? ' (pinned)' : ''}${rolledBack ? ' (rolled back)' : ''}` +
    `${impactSuffix}${changeSuffix}`;

  return (
    <g
      className={className}
      role="img"
      aria-label={ariaLabel}
      data-testid={`station-${versionId}`}
      data-pinned={pinned}
      data-reached={reached}
      data-fresh={fresh}
      data-rolled-back={rolledBack}
      data-impact-state={impactState}
      data-impact-level={impactLevel ?? undefined}
      data-change-level={showsChangeLevel ? badgeLevel : undefined}
    >
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        className={styles.stationDot}
        style={{ stroke: hue, fill: pinned ? hue : 'var(--panel-solid)' }}
      />
      <text
        x={cx}
        y={cy - 13}
        textAnchor="middle"
        className={`${styles.stationLabel} mono`}
        style={pinned ? { fill: hue } : undefined}
      >
        {label}
      </text>
      {badgeLevel ? (
        <text
          x={cx}
          y={cy + BADGE_DY}
          textAnchor="middle"
          className={`${styles.levelBadge} ${LEVEL_CLASS[badgeLevel]}`}
          data-testid={`station-badge-${versionId}`}
        >
          {`▲ ${badgeLevel}`}
        </text>
      ) : null}
    </g>
  );
}
