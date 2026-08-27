import { render, screen } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { describe, expect, it } from 'vitest';

import { Station, type StationProps } from './station';

const BASE: StationProps = {
  versionId: 'comp-api-v4',
  label: '2.4.0',
  cx: 400,
  cy: 100,
  hue: '#5ad1ff',
  pinned: true,
  reached: true,
  fresh: false,
  rolledBack: false,
};

function renderStation(overrides: Partial<StationProps> = {}): HTMLElement {
  const svg = (children: ReactNode): ReactElement => <svg>{children}</svg>;
  render(svg(<Station {...BASE} {...overrides} />));
  return screen.getByTestId('station-comp-api-v4');
}

describe('Station — impact highlight', () => {
  it('rings the source and says so in its accessible name', () => {
    const station = renderStation({ impactState: 'source' });

    expect(station).toHaveAttribute('data-impact-state', 'source');
    expect(station.getAttribute('class')).toContain('stationSource');
    expect(station).toHaveAttribute('aria-label', expect.stringContaining('(source)'));
    expect(screen.queryByTestId('station-badge-comp-api-v4')).not.toBeInTheDocument();
  });

  it('badges an impacted station with a glyph and the level in words', () => {
    const station = renderStation({ impactState: 'impacted', impactLevel: 'minor' });

    expect(station).toHaveAttribute('data-impact-level', 'minor');
    expect(station.getAttribute('class')).toContain('stationImpacted');
    expect(station).toHaveAttribute('aria-label', expect.stringContaining('impact: minor'));

    const badge = screen.getByTestId('station-badge-comp-api-v4');
    expect(badge).toHaveTextContent('▲ minor');
    expect(badge.getAttribute('class')).toContain('levelMinor');
  });

  it('dims a station outside the blast radius', () => {
    const station = renderStation({ impactState: 'dimmed' });

    expect(station).toHaveAttribute('data-impact-state', 'dimmed');
    expect(station.getAttribute('class')).toContain('stationDimmed');
    expect(station).not.toHaveAttribute('data-impact-level');
  });

  it('gates the impact glow behind the reduced-motion seam', () => {
    expect(
      renderStation({ impactState: 'impacted', impactLevel: 'major', animated: true }).getAttribute(
        'class',
      ),
    ).toContain('animated');
  });
});

describe('Station — release-frozen change level', () => {
  it('badges the pinned version with its own change level', () => {
    const station = renderStation({ changeLevel: 'patch' });

    expect(station).toHaveAttribute('data-change-level', 'patch');
    expect(station).toHaveAttribute('aria-label', expect.stringContaining('change: patch'));

    const badge = screen.getByTestId('station-badge-comp-api-v4');
    expect(badge).toHaveTextContent('▲ patch');
    expect(badge.getAttribute('class')).toContain('levelPatch');
  });

  it('renders no badge for a version absent from the latest release', () => {
    const station = renderStation({ changeLevel: null });

    expect(station).not.toHaveAttribute('data-change-level');
    expect(screen.queryByTestId('station-badge-comp-api-v4')).not.toBeInTheDocument();
  });

  it('yields the badge slot to the impact badge while a selection is active', () => {
    const station = renderStation({
      impactState: 'impacted',
      impactLevel: 'major',
      changeLevel: 'patch',
    });

    expect(station).toHaveAttribute('data-impact-level', 'major');
    expect(station).not.toHaveAttribute('data-change-level');
    expect(screen.getByTestId('station-badge-comp-api-v4')).toHaveTextContent('▲ major');
  });

  it('suppresses the change badge on a dimmed station too', () => {
    const station = renderStation({ impactState: 'dimmed', changeLevel: 'minor' });

    expect(station).not.toHaveAttribute('data-change-level');
    expect(screen.queryByTestId('station-badge-comp-api-v4')).not.toBeInTheDocument();
  });
});
