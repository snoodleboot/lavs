import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { seedComponents, seedDependencies } from '@/mocks';
import type { Component, Dependency } from '@/types';

import { DependencyEdges } from './dependency-edges';
import { GUTTER_DEPTH, LABEL_COLUMN_LEFT, yOf } from './geometry';

const COMPONENTS: readonly Component[] = seedComponents();

function svg(children: React.ReactNode): React.ReactElement {
  return <svg>{children}</svg>;
}

/** Every numeric x in a path `d`, i.e. the first of each coordinate pair. */
function xValuesOf(d: string): number[] {
  const numbers = (d.match(/-?\d+(\.\d+)?/g) ?? []).map(Number);
  return numbers.filter((_, index) => index % 2 === 0);
}

describe('DependencyEdges', () => {
  it('renders exactly one arc per dependency', () => {
    const dependencies = seedDependencies();
    render(svg(<DependencyEdges dependencies={dependencies} components={COMPONENTS} />));

    expect(screen.getByTestId('dependency-edges')).toBeInTheDocument();
    for (const dependency of dependencies) {
      expect(screen.getByTestId(`dependency-edge-${dependency.id}`)).toBeInTheDocument();
    }
    expect(screen.getAllByTestId(/^dependency-edge-/)).toHaveLength(dependencies.length);
  });

  it('renders no arc when there are no dependencies', () => {
    render(svg(<DependencyEdges dependencies={[]} components={COMPONENTS} />));

    expect(screen.getByTestId('dependency-edges')).toBeInTheDocument();
    expect(screen.queryAllByTestId(/^dependency-edge-/)).toHaveLength(0);
  });

  it('skips an edge whose endpoint is absent from the timeline', () => {
    const orphan: Dependency = {
      id: 'dep-orphan',
      product_id: 'prod-aurora',
      from_component_id: 'comp-ghost',
      to_component_id: 'comp-api',
      created_at: '2026-05-12T12:00:00.000Z',
    };
    const reversed: Dependency = {
      ...orphan,
      id: 'dep-orphan-to',
      from_component_id: 'comp-ui',
      to_component_id: 'comp-ghost',
    };

    render(svg(<DependencyEdges dependencies={[orphan, reversed]} components={COMPONENTS} />));

    expect(screen.queryAllByTestId(/^dependency-edge-/)).toHaveLength(0);
  });

  it('anchors both endpoints on the label-column edge at their lane centres', () => {
    // comp-ui (index 1) depends on comp-api (index 0).
    const dependencies = seedDependencies().filter((edge) => edge.id === 'dep-ui-api');
    render(svg(<DependencyEdges dependencies={dependencies} components={COMPONENTS} />));

    const d = screen.getByTestId('dependency-edge-dep-ui-api').getAttribute('d') ?? '';
    const fromY = yOf(1, COMPONENTS.length);
    const toY = yOf(0, COMPONENTS.length);

    expect(d.startsWith(`M ${LABEL_COLUMN_LEFT} ${fromY} `)).toBe(true);
    expect(d.endsWith(`${LABEL_COLUMN_LEFT} ${toY}`)).toBe(true);
  });

  it('keeps every arc inside the reserved gutter, left of the label column', () => {
    render(svg(<DependencyEdges dependencies={seedDependencies()} components={COMPONENTS} />));

    for (const path of screen.getAllByTestId(/^dependency-(edge|arrow)-/)) {
      for (const x of xValuesOf(path.getAttribute('d') ?? '')) {
        expect(x).toBeLessThanOrEqual(LABEL_COLUMN_LEFT);
        expect(x).toBeGreaterThanOrEqual(LABEL_COLUMN_LEFT - GUTTER_DEPTH);
      }
    }
  });

  it('draws an arrowhead at the dependency (to) endpoint', () => {
    const dependencies = seedDependencies().filter((edge) => edge.id === 'dep-ui-api');
    render(svg(<DependencyEdges dependencies={dependencies} components={COMPONENTS} />));

    const arrow = screen.getByTestId('dependency-arrow-dep-ui-api').getAttribute('d') ?? '';
    // Tip sits on comp-api's lane (index 0), not on comp-ui's.
    expect(arrow.startsWith(`M ${LABEL_COLUMN_LEFT} ${yOf(0, COMPONENTS.length)} `)).toBe(true);
  });

  it('is decorative: the layer is hidden from assistive technology', () => {
    render(svg(<DependencyEdges dependencies={seedDependencies()} components={COMPONENTS} />));

    expect(screen.getByTestId('dependency-edges')).toHaveAttribute('aria-hidden', 'true');
  });
});
