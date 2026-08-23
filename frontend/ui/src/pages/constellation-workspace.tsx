import { useCallback, useMemo, useState, type ReactNode } from 'react';

import { AppShell } from '@/app/app-shell';
import { useAuth } from '@/features/auth';
import {
  ConstellationView,
  DEFAULT_PRODUCT_BASE,
  buildTimeAxis,
  deriveManifest,
  derivedProductVersion,
  useGraph,
  useImpact,
  useScrub,
} from '@/features/constellation';
import { useProductEvents } from '@/features/live';
import { ProductNav } from '@/features/nav';
import { CommandPalette, useCommandPalette, type PaletteAction } from '@/features/palette';
import {
  CutReleaseButton,
  ProductVersionReadout,
  ReleaseLedger,
  useReleases,
} from '@/features/releases';
import { formatVersion, hueForIndex } from '@/lib';
import type { ChangeLevel, Release, Timeline } from '@/types';

import styles from './constellation-workspace.module.css';

interface ConstellationWorkspaceProps {
  readonly productId: string;
  readonly timeline: Timeline;
  readonly onSelectProduct: (productId: string) => void;
}

/**
 * The composed Constellation view for a resolved product: R1 SVG + scrub, R2 HUD readout /
 * cut / ledger, R3 live SSE overlay, R4 nav + ⌘K palette. Receives a guaranteed timeline so
 * the axis/scrub hooks initialise against real data (position defaults to "now").
 */
export function ConstellationWorkspace({
  productId,
  timeline,
  onSelectProduct,
}: ConstellationWorkspaceProps): ReactNode {
  const { logout } = useAuth();
  const axis = useMemo(() => buildTimeAxis(timeline), [timeline]);
  const { position, setPosition, stepLeft, stepRight } = useScrub(axis.maxTick);

  const manifest = useMemo(
    () => deriveManifest(timeline, axis, position),
    [timeline, axis, position],
  );
  const pinnedCount = manifest.filter((entry) => entry.version !== null).length;

  const graphQuery = useGraph(productId);
  const releasesQuery = useReleases(productId);

  // Impact selection. The `key={productId}` remount in ConstellationPage clears this on a
  // product switch, so no effect is needed to reset it.
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(null);
  const impactQuery = useImpact(productId, selectedComponentId);

  // Derived off the SELECTION, not the query: clearing the selection must stop the tinting
  // immediately even while the previous blast radius is still cached.
  const impactedByComponent = useMemo<ReadonlyMap<string, ChangeLevel>>(
    () =>
      new Map(
        selectedComponentId
          ? (impactQuery.data?.impacted.map((entry) => [
              entry.component_id,
              entry.projected_change_level,
            ]) ?? [])
          : [],
      ),
    [selectedComponentId, impactQuery.data],
  );
  const base = releasesQuery.data?.[0]?.product_version ?? DEFAULT_PRODUCT_BASE;
  const productVersion = derivedProductVersion(base, pinnedCount > 0);

  // Live SSE overlay: pulsing/dimming sets fed into the SVG; ledger reconciles on release.cut.
  const live = useProductEvents(productId);
  const palette = useCommandPalette();

  // Reopen a frozen release: pin the meridian at the latest tick it captured.
  const reopen = useCallback(
    (release: Release): void => {
      const ticks = release.components
        .map((component) => axis.tickOf(component.version_id))
        .filter((tick) => tick >= 0);
      if (ticks.length > 0) setPosition(Math.max(...ticks));
    },
    [axis, setPosition],
  );

  const actions = useMemo<PaletteAction[]>(
    () => [
      { id: 'scrub-later', label: 'Scrub later', hint: '→', run: stepRight },
      { id: 'scrub-earlier', label: 'Scrub earlier', hint: '←', run: stepLeft },
      { id: 'scrub-now', label: 'Jump to now', run: () => setPosition(axis.maxTick) },
      { id: 'scrub-origin', label: 'Jump to origin', run: () => setPosition(0) },
      { id: 'sign-out', label: 'Sign out', run: () => void logout() },
    ],
    [stepRight, stepLeft, setPosition, axis.maxTick, logout],
  );

  const productLabel = `${timeline.product.name} · ${timeline.components.length} components`;

  return (
    <AppShell
      productLabel={productLabel}
      headerActions={
        <>
          <ProductNav productId={productId} onSelect={onSelectProduct} />
          <button
            type="button"
            className={styles.paletteTrigger}
            onClick={palette.toggle}
            aria-haspopup="dialog"
            aria-label="Open command palette (Command or Control K)"
          >
            ⌘K
          </button>
          <span
            className={styles.live}
            data-connected={live.connected}
            role="status"
            aria-label={live.connected ? 'Live updates connected' : 'Live updates offline'}
          >
            {live.connected ? 'live' : 'offline'}
          </span>
        </>
      }
    >
      <div className={styles.layout}>
        <div className={styles.canvasRow}>
          <div className={styles.canvasWrap}>
            <ConstellationView
              timeline={timeline}
              axis={axis}
              position={position}
              onPositionChange={setPosition}
              freshVersionIds={live.freshVersionIds}
              rolledBackVersionIds={live.rolledBackVersionIds}
              dependencies={graphQuery.data?.edges ?? []}
              selectedComponentId={selectedComponentId}
              impactedByComponent={impactedByComponent}
              onSelectComponent={setSelectedComponentId}
            />
            <p className={styles.hint}>
              Time flows left → right · the right edge is <b>now</b>. The bright line is a release
              you haven&apos;t cut yet.
            </p>
          </div>

          <aside className={styles.hud} aria-label="Release controls">
            <ProductVersionReadout productVersion={productVersion} tick={position} />
            <div className={styles.manifestCard}>
              <h3 className={styles.cardHeading}>Pinned manifest</h3>
              <ul className={styles.manifest}>
                {manifest.map((entry, index) => (
                  <li key={entry.component.id} className={styles.manifestRow}>
                    <span
                      className={styles.swatch}
                      style={{ background: hueForIndex(index) }}
                      aria-hidden="true"
                    />
                    <span className={styles.manifestName}>{entry.component.name}</span>
                    <span className={`${styles.manifestVersion} mono`}>
                      {entry.version ? formatVersion(entry.version) : '—'}
                    </span>
                  </li>
                ))}
              </ul>
              <CutReleaseButton productId={productId} disabled={pinnedCount === 0} />
            </div>
          </aside>
        </div>

        <ReleaseLedger productId={productId} onReopen={reopen} />
      </div>

      <CommandPalette
        actions={actions}
        open={palette.open}
        onClose={() => palette.setOpen(false)}
      />
    </AppShell>
  );
}
