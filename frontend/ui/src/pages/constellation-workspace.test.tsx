import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { seedComponents, seedProduct } from '@/mocks';
import { renderWithProviders } from '@/test';
import type { Timeline } from '@/types';

import { ConstellationWorkspace } from './constellation-workspace';

function seedTimeline(): Timeline {
  return { product: seedProduct(), components: seedComponents() };
}

describe('ConstellationWorkspace', () => {
  it('renders the readout, manifest, cut control and ledger for the seeded product', () => {
    renderWithProviders(
      <ConstellationWorkspace
        productId="prod-aurora"
        timeline={seedTimeline()}
        onSelectProduct={() => {}}
      />,
    );

    // Derived product-version readout is present.
    expect(screen.getByText(/derived product version/i)).toBeInTheDocument();
    // Manifest lists the latest active version per component (meridian defaults to "now").
    expect(screen.getAllByText('2.4.0').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: /cut release/i })).toBeInTheDocument();
  });

  it('opens the command palette with ⌘K and runs an action', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ConstellationWorkspace
        productId="prod-aurora"
        timeline={seedTimeline()}
        onSelectProduct={() => {}}
      />,
    );

    await user.keyboard('{Meta>}k{/Meta}');
    const dialog = await screen.findByRole('dialog');
    expect(dialog).toBeInTheDocument();

    // Run "Jump to origin" and the palette closes.
    await user.click(within(dialog).getByText(/jump to origin/i));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('lights the blast radius when a lane label is selected, and clears it on Escape', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ConstellationWorkspace
        productId="prod-aurora"
        timeline={seedTimeline()}
        onSelectProduct={() => {}}
      />,
    );

    const apiLabel = screen.getByTestId('lane-label-comp-api');
    expect(apiLabel).toHaveAttribute('aria-pressed', 'false');

    await user.click(apiLabel);
    expect(apiLabel).toHaveAttribute('aria-pressed', 'true');

    // The seeded graph puts ui and cli one hop from api, helm two.
    await waitFor(() =>
      expect(screen.getByTestId('station-comp-ui-v4')).toHaveAttribute(
        'data-impact-level',
        'minor',
      ),
    );
    expect(screen.getByTestId('station-comp-helm-v2')).toHaveAttribute(
      'data-impact-level',
      'patch',
    );
    expect(screen.getByTestId('station-comp-api-v4')).toHaveAttribute(
      'data-impact-state',
      'source',
    );
    // One badge per impacted lane — never one per version node.
    expect(screen.getAllByTestId(/^station-badge-/)).toHaveLength(3);

    await user.keyboard('{Escape}');
    await waitFor(() =>
      expect(screen.getByTestId('station-comp-ui-v4')).not.toHaveAttribute('data-impact-level'),
    );
    expect(apiLabel).toHaveAttribute('aria-pressed', 'false');
  });

  it('scrubs the meridian with the keyboard, updating the tick readout', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ConstellationWorkspace
        productId="prod-aurora"
        timeline={seedTimeline()}
        onSelectProduct={() => {}}
      />,
    );

    const slider = screen.getByRole('slider', { name: /release meridian/i });
    const before = slider.getAttribute('aria-valuenow');
    slider.focus();
    await user.keyboard('{ArrowLeft}');
    await waitFor(() => {
      expect(slider.getAttribute('aria-valuenow')).not.toBe(before);
    });
  });
});
