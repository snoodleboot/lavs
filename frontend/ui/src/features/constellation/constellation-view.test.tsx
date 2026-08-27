import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { seedComponents, seedDependencies, seedProduct } from '@/mocks';
import type { ChangeLevel, Timeline } from '@/types';

import { ConstellationView } from './constellation-view';
import { LABEL_COLUMN_LEFT, LABEL_MAX_WIDTH, buildTimeAxis, labelWidth } from './geometry';

function makeTimeline(): Timeline {
  return { product: seedProduct(), components: seedComponents() };
}

function mockSvgRect(svg: Element): void {
  // jsdom returns zeros; give the SVG a real box so pointer math runs.
  svg.getBoundingClientRect = (): DOMRect => ({
    x: 0,
    y: 0,
    left: 0,
    top: 0,
    right: 900,
    bottom: 460,
    width: 900,
    height: 460,
    toJSON: () => ({}),
  });
}

/**
 * jsdom lacks a PointerEvent constructor and its fireEvent.pointer* drops clientX,
 * so dispatch a MouseEvent (which honours clientX) under the pointer event type —
 * React's onPointer* handlers fire on the event type regardless of the class.
 */
function firePointer(target: Element, type: string, clientX?: number): void {
  const event = new MouseEvent(type, { bubbles: true, cancelable: true, clientX: clientX ?? 0 });
  fireEvent(target, event);
}

/** comp-api's blast radius: ui/cli directly, helm transitively. */
const IMPACT: ReadonlyMap<string, ChangeLevel> = new Map<string, ChangeLevel>([
  ['comp-ui', 'minor'],
  ['comp-cli', 'minor'],
  ['comp-helm', 'patch'],
]);

function stubReducedMotion(matches: boolean): void {
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({
      matches,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
}

describe('ConstellationView', () => {
  it('renders a stream and stations for each seed component', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);

    render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={axis.maxTick}
        onPositionChange={vi.fn()}
      />,
    );

    for (const component of timeline.components) {
      expect(screen.getByTestId(`stream-${component.id}`)).toBeInTheDocument();
      for (const version of component.versions) {
        expect(screen.getByTestId(`station-${version.id}`)).toBeInTheDocument();
      }
    }
  });

  it('marks the pinned station at the meridian position', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);

    render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={axis.maxTick}
        onPositionChange={vi.fn()}
      />,
    );

    // At "now", the active api version is pinned; an earlier one is not.
    expect(screen.getByTestId('station-comp-api-v4')).toHaveAttribute('data-pinned', 'true');
    expect(screen.getByTestId('station-comp-api-v0')).toHaveAttribute('data-pinned', 'false');
    // A connector is drawn from the pinned station to the meridian.
    expect(screen.getByTestId('connector-comp-api')).toBeInTheDocument();
  });

  it('dims stations the meridian has not yet reached', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);

    render(
      <ConstellationView timeline={timeline} axis={axis} position={0} onPositionChange={vi.fn()} />,
    );

    // At tick 0, ui's first station (day 2 → tick 1) is not yet reached.
    expect(screen.getByTestId('station-comp-ui-v0')).toHaveAttribute('data-reached', 'false');
    expect(screen.getByTestId('station-comp-api-v0')).toHaveAttribute('data-reached', 'true');
  });

  it('exposes a focusable slider meridian and moves it with the keyboard', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);
    const onPositionChange = vi.fn();

    render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={5}
        onPositionChange={onPositionChange}
      />,
    );

    const slider = screen.getByRole('slider', { name: 'Release meridian' });
    expect(slider).toHaveAttribute('aria-valuemin', '0');
    expect(slider).toHaveAttribute('aria-valuemax', String(axis.maxTick));
    expect(slider).toHaveAttribute('aria-valuenow', '5');
    expect(slider).toHaveAttribute('tabindex', '0');

    slider.focus();

    fireEvent.keyDown(slider, { key: 'ArrowRight' });
    expect(onPositionChange).toHaveBeenLastCalledWith(6);

    fireEvent.keyDown(slider, { key: 'ArrowLeft' });
    expect(onPositionChange).toHaveBeenLastCalledWith(4);

    fireEvent.keyDown(slider, { key: 'Home' });
    expect(onPositionChange).toHaveBeenLastCalledWith(0);

    fireEvent.keyDown(slider, { key: 'End' });
    expect(onPositionChange).toHaveBeenLastCalledWith(axis.maxTick);

    onPositionChange.mockClear();
    fireEvent.keyDown(slider, { key: 'a' });
    expect(onPositionChange).not.toHaveBeenCalled();
  });

  it('scrubs by dragging near the meridian', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);
    const onPositionChange = vi.fn();

    const { container } = render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={axis.maxTick}
        onPositionChange={onPositionChange}
      />,
    );

    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    mockSvgRect(svg!);

    // Meridian sits at the right edge (x == 830 for maxTick). Grab it and drag left.
    firePointer(svg!, 'pointerdown', 830);
    expect(onPositionChange).toHaveBeenCalledWith(axis.maxTick);

    firePointer(svg!, 'pointermove', 120);
    expect(onPositionChange).toHaveBeenLastCalledWith(0);

    firePointer(svg!, 'pointerup');
    // After release, moving no longer scrubs.
    onPositionChange.mockClear();
    firePointer(svg!, 'pointermove', 475);
    expect(onPositionChange).not.toHaveBeenCalled();
  });

  it('ignores a pointer-down far from the meridian', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);
    const onPositionChange = vi.fn();

    const { container } = render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={axis.maxTick}
        onPositionChange={onPositionChange}
      />,
    );

    const svg = container.querySelector('svg');
    mockSvgRect(svg!);
    // Far from the right-edge meridian → no scrub.
    firePointer(svg!, 'pointerdown', 130);
    expect(onPositionChange).not.toHaveBeenCalled();
  });

  it('paints the dependency-edge layer before the first stream', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);

    render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={axis.maxTick}
        onPositionChange={vi.fn()}
        dependencies={seedDependencies()}
      />,
    );

    const edges = screen.getByTestId('dependency-edges');
    const firstStream = screen.getByTestId(`stream-${timeline.components[0]!.id}`);
    // DOCUMENT_POSITION_FOLLOWING: the streams come after the edges, so stations paint on top.
    expect(edges.compareDocumentPosition(firstStream) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
    expect(screen.getByTestId('dependency-edge-dep-ui-api')).toBeInTheDocument();
  });

  it('bounds every lane label to the reserved label column', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);

    const { container } = render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={axis.maxTick}
        onPositionChange={vi.fn()}
      />,
    );

    for (const component of timeline.components) {
      const label = screen.getByText(component.name);
      const width = Number(label.getAttribute('textLength'));
      expect(width).toBe(labelWidth(component.name));
      expect(width).toBeLessThanOrEqual(LABEL_MAX_WIDTH);
      // End-anchored: the leftmost glyph never enters the arc gutter.
      expect(Number(label.getAttribute('x')) - width).toBeGreaterThanOrEqual(LABEL_COLUMN_LEFT);
    }
    expect(container.querySelectorAll('text[text-anchor="end"]').length).toBe(
      timeline.components.length,
    );
  });

  it('flags fresh and rolled-back stations for non-color signalling', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);

    render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={axis.maxTick}
        onPositionChange={vi.fn()}
        freshVersionIds={new Set(['comp-api-v4'])}
        rolledBackVersionIds={new Set(['comp-api-v3'])}
      />,
    );

    expect(screen.getByTestId('station-comp-api-v4')).toHaveAttribute('data-fresh', 'true');
    const rolledBack = screen.getByTestId('station-comp-api-v3');
    expect(rolledBack).toHaveAttribute('data-rolled-back', 'true');
    expect(rolledBack).toHaveAttribute('aria-label', expect.stringContaining('rolled back'));
  });
});

describe('ConstellationView — impact selection', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function renderView(overrides: Partial<Parameters<typeof ConstellationView>[0]> = {}) {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);
    const result = render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={axis.maxTick}
        onPositionChange={vi.fn()}
        dependencies={seedDependencies()}
        {...overrides}
      />,
    );
    return { ...result, timeline, axis };
  }

  it('exposes each lane label as a toggle whose pressed state tracks the selection', () => {
    renderView({ selectedComponentId: 'comp-api' });

    expect(screen.getByTestId('lane-label-comp-api')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('lane-label-comp-ui')).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button', { name: 'lavs-api' })).toBeInTheDocument();
  });

  it('selects with a click and with Enter or Space', () => {
    const onSelectComponent = vi.fn();
    renderView({ onSelectComponent });
    const label = screen.getByTestId('lane-label-comp-api');

    fireEvent.click(label);
    expect(onSelectComponent).toHaveBeenLastCalledWith('comp-api');

    fireEvent.keyDown(label, { key: 'Enter' });
    expect(onSelectComponent).toHaveBeenLastCalledWith('comp-api');

    fireEvent.keyDown(label, { key: ' ' });
    expect(onSelectComponent).toHaveBeenLastCalledWith('comp-api');

    onSelectComponent.mockClear();
    fireEvent.keyDown(label, { key: 'x' });
    expect(onSelectComponent).not.toHaveBeenCalled();
  });

  it('toggles the active selection off and clears it on Escape', () => {
    const onSelectComponent = vi.fn();
    const { container } = renderView({ selectedComponentId: 'comp-api', onSelectComponent });

    fireEvent.click(screen.getByTestId('lane-label-comp-api'));
    expect(onSelectComponent).toHaveBeenLastCalledWith(null);

    fireEvent.keyDown(container.querySelector('svg')!, { key: 'Escape' });
    expect(onSelectComponent).toHaveBeenLastCalledWith(null);
  });

  it('never starts a meridian scrub from the lane-label toggle', () => {
    const onPositionChange = vi.fn();
    // Meridian at tick 0 sits at x=120, within the 28px grab zone of the label column.
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);
    const { container } = render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={0}
        onPositionChange={onPositionChange}
        onSelectComponent={vi.fn()}
      />,
    );
    mockSvgRect(container.querySelector('svg')!);

    firePointer(screen.getByTestId('lane-label-comp-api'), 'pointerdown', 100);

    expect(onPositionChange).not.toHaveBeenCalled();
  });

  it('paints impact on the pinned station only, never across a lane history', () => {
    renderView({ selectedComponentId: 'comp-api', impactedByComponent: IMPACT });

    // The pinned ui station carries the projected level…
    const pinnedUi = screen.getByTestId('station-comp-ui-v4');
    expect(pinnedUi).toHaveAttribute('data-pinned', 'true');
    expect(pinnedUi).toHaveAttribute('data-impact-level', 'minor');
    expect(pinnedUi).toHaveAttribute('data-impact-state', 'impacted');

    // …and no historical station in the same lane does.
    for (const versionId of ['comp-ui-v0', 'comp-ui-v1', 'comp-ui-v2', 'comp-ui-v3']) {
      const station = screen.getByTestId(`station-${versionId}`);
      expect(station).not.toHaveAttribute('data-impact-level');
      expect(station).not.toHaveAttribute('data-impact-state');
    }

    // Exactly one impact badge per impacted lane (ui, cli, helm).
    expect(screen.getAllByTestId(/^station-badge-/)).toHaveLength(3);
  });

  it('rings the source and dims everything outside the blast radius', () => {
    renderView({
      selectedComponentId: 'comp-api',
      impactedByComponent: new Map<string, ChangeLevel>([['comp-ui', 'minor']]),
    });

    expect(screen.getByTestId('station-comp-api-v4')).toHaveAttribute(
      'data-impact-state',
      'source',
    );
    expect(screen.getByTestId('station-comp-ui-v4')).toHaveAttribute(
      'data-impact-state',
      'impacted',
    );
    expect(screen.getByTestId('station-comp-cli-v1')).toHaveAttribute(
      'data-impact-state',
      'dimmed',
    );
  });

  it('leaves every station unstated when nothing is selected', () => {
    renderView();

    expect(screen.getByTestId('station-comp-api-v4')).not.toHaveAttribute('data-impact-state');
    expect(screen.queryAllByTestId(/^station-badge-/)).toHaveLength(0);
  });

  it('brightens only the edges inside the blast radius', () => {
    const { container } = renderView({
      selectedComponentId: 'comp-api',
      impactedByComponent: new Map<string, ChangeLevel>([['comp-ui', 'minor']]),
    });

    const active = (id: string): string | null =>
      container
        .querySelector(`[data-testid="dependency-edge-${id}"]`)!
        .closest('[data-active]')!
        .getAttribute('data-active');

    // comp-ui -> comp-api: both ends in the radius.
    expect(active('dep-ui-api')).toBe('true');
    // comp-cli -> comp-api: cli is outside the (trimmed) radius here.
    expect(active('dep-cli-api')).toBe('false');
  });

  it('collapses the impact glow under prefers-reduced-motion', () => {
    stubReducedMotion(true);
    renderView({ selectedComponentId: 'comp-api', impactedByComponent: IMPACT });

    expect(screen.getByTestId('station-comp-api-v4').getAttribute('class')).not.toContain(
      'animated',
    );
    expect(screen.getByTestId('station-comp-ui-v4').getAttribute('class')).not.toContain(
      'animated',
    );
  });

  it('animates the blast radius when motion is not reduced', () => {
    stubReducedMotion(false);
    renderView({ selectedComponentId: 'comp-api', impactedByComponent: IMPACT });

    expect(screen.getByTestId('station-comp-ui-v4').getAttribute('class')).toContain('animated');
  });
});

describe('ConstellationView — release-frozen change levels', () => {
  it('badges the pinned version keyed by version id, never by component', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);
    // Only the latest api version is in the release; an older ui version is not.
    const changeLevelByVersion = new Map<string, ChangeLevel | null>([
      ['comp-api-v4', 'minor'],
      ['comp-ui-v0', 'major'],
    ]);

    render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={axis.maxTick}
        onPositionChange={vi.fn()}
        changeLevelByVersion={changeLevelByVersion}
      />,
    );

    expect(screen.getByTestId('station-comp-api-v4')).toHaveAttribute('data-change-level', 'minor');
    // At "now" the pinned ui version is v4, which is not in the release → no badge, and the
    // release's entry for the historical v0 must not leak onto it.
    expect(screen.getByTestId('station-comp-ui-v4')).not.toHaveAttribute('data-change-level');
    expect(screen.getByTestId('station-comp-ui-v0')).not.toHaveAttribute('data-change-level');
    expect(screen.getAllByTestId(/^station-badge-/)).toHaveLength(1);
  });

  it('follows the meridian: scrubbing back pins the version the release froze', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);
    const changeLevelByVersion = new Map<string, ChangeLevel | null>([['comp-ui-v0', 'major']]);

    render(
      <ConstellationView
        timeline={timeline}
        axis={axis}
        position={axis.tickOf('comp-ui-v0')}
        onPositionChange={vi.fn()}
        changeLevelByVersion={changeLevelByVersion}
      />,
    );

    expect(screen.getByTestId('station-comp-ui-v0')).toHaveAttribute('data-change-level', 'major');
  });
});
