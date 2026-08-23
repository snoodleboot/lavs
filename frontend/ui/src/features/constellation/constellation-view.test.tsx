import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { seedComponents, seedDependencies, seedProduct } from '@/mocks';
import type { Timeline } from '@/types';

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
