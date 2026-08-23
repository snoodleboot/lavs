import type { ReactNode } from 'react';

import type { BumpLevel, ChangeLevel } from '@/types';

import { formatBumpRationale } from './bump-rationale';
import styles from './product-version-readout.module.css';

const LEVEL_CLASS: Readonly<Record<ChangeLevel, string>> = {
  // `noUncheckedIndexedAccess` widens CSS-module lookups to `string | undefined`.
  major: styles.levelMajor ?? '',
  minor: styles.levelMinor ?? '',
  patch: styles.levelPatch ?? '',
};

export interface ProductVersionReadoutProps {
  /** The client-derived product version for the current meridian position. */
  readonly productVersion: string;
  /** The meridian tick (ordinal time position) being read out. */
  readonly tick: number;
  /** P9 derived bump of the latest CUT release (`none`/`null` renders nothing). */
  readonly bumpLevel?: BumpLevel | null;
  /** P9 raw JSON rationale for that bump — shaped through `formatBumpRationale`. */
  readonly bumpRationale?: string | null;
  /** Whether the meridian sits at "now". The bump belongs to a cut release, not to a
      scrubbed-back position, so off "now" the card shows the derived version alone. */
  readonly atNow?: boolean;
}

/**
 * The "Release Meridian" card: a big luminous derived product version plus a `t = N` tick
 * readout. Purely presentational — the derivation happens upstream (R1).
 */
export function ProductVersionReadout({
  productVersion,
  tick,
  bumpLevel = null,
  bumpRationale = null,
  atNow = false,
}: ProductVersionReadoutProps): ReactNode {
  // The derived version is scrub-derived while the bump is frozen into the latest cut
  // release; showing both away from "now" would let the card contradict itself.
  const showsBump = atNow && bumpLevel !== null && bumpLevel !== 'none';
  const rationale = showsBump ? formatBumpRationale(bumpRationale) : null;

  return (
    <section className={styles.card} aria-labelledby="meridian-title">
      <div className={styles.head}>
        <h3 id="meridian-title" className={styles.title}>
          Release Meridian
        </h3>
        {showsBump ? (
          <span className={styles.bumpGroup}>
            <span className={styles.bumpLabel}>latest cut</span>
            <span
              className={`${styles.bump} ${LEVEL_CLASS[bumpLevel]}`}
              data-testid="bump-level"
              data-level={bumpLevel}
            >
              {`▲ ${bumpLevel}`}
            </span>
          </span>
        ) : null}
        <span className={styles.tick} data-testid="meridian-tick">
          t = {tick}
        </span>
      </div>
      <div className={styles.pv}>
        <span className={styles.pvLabel}>Derived product version</span>
        <span className={styles.pvValue} data-testid="product-version">
          {productVersion}
        </span>
      </div>
      {rationale ? (
        <p className={styles.rationale} data-testid="bump-rationale">
          {rationale}
        </p>
      ) : null}
    </section>
  );
}
