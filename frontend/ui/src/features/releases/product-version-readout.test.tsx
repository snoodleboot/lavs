import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SEED_BUMP_RATIONALE } from '@/mocks';

import { ProductVersionReadout } from './product-version-readout';

describe('ProductVersionReadout', () => {
  it('renders the derived product version and the tick readout', () => {
    render(<ProductVersionReadout productVersion="5.1.0" tick={13} />);

    expect(screen.getByTestId('product-version')).toHaveTextContent('5.1.0');
    expect(screen.getByTestId('meridian-tick')).toHaveTextContent('t = 13');
    expect(screen.getByText(/derived product version/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /release meridian/i })).toBeInTheDocument();
    expect(screen.queryByTestId('bump-level')).not.toBeInTheDocument();
  });

  it('shows the latest cut release bump and its formatted rationale at "now"', () => {
    render(
      <ProductVersionReadout
        productVersion="5.1.0"
        tick={11}
        bumpLevel="minor"
        bumpRationale={SEED_BUMP_RATIONALE}
        atNow
      />,
    );

    const badge = screen.getByTestId('bump-level');
    expect(badge).toHaveTextContent('▲ minor');
    expect(badge).toHaveAttribute('data-level', 'minor');
    expect(badge.getAttribute('class')).toContain('levelMinor');
    expect(screen.getByText(/latest cut/i)).toBeInTheDocument();

    // The wire value is JSON; the card must show the shaped line, never the raw payload.
    const rationale = screen.getByTestId('bump-rationale');
    expect(rationale).toHaveTextContent('3 of 4 components changed.');
    expect(rationale.textContent).not.toContain('{');
  });

  it('hides the bump once the meridian scrubs away from "now"', () => {
    render(
      <ProductVersionReadout
        productVersion="5.1.0"
        tick={4}
        bumpLevel="major"
        bumpRationale={SEED_BUMP_RATIONALE}
        atNow={false}
      />,
    );

    expect(screen.queryByTestId('bump-level')).not.toBeInTheDocument();
    expect(screen.queryByTestId('bump-rationale')).not.toBeInTheDocument();
  });

  it('renders nothing for a `none` or absent bump level', () => {
    const { rerender } = render(
      <ProductVersionReadout productVersion="5.1.0" tick={11} bumpLevel="none" atNow />,
    );
    expect(screen.queryByTestId('bump-level')).not.toBeInTheDocument();

    rerender(<ProductVersionReadout productVersion="5.1.0" tick={11} bumpLevel={null} atNow />);
    expect(screen.queryByTestId('bump-level')).not.toBeInTheDocument();
  });

  it('shows the badge without a rationale line when the rationale is absent', () => {
    render(
      <ProductVersionReadout
        productVersion="5.1.0"
        tick={11}
        bumpLevel="patch"
        bumpRationale={null}
        atNow
      />,
    );

    expect(screen.getByTestId('bump-level')).toHaveTextContent('▲ patch');
    expect(screen.queryByTestId('bump-rationale')).not.toBeInTheDocument();
  });
});
