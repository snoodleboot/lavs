import { expect, test, type Page } from '@playwright/test';

interface AxeResult {
  readonly violations: readonly { readonly id: string; readonly impact: string | null }[];
}

/** Run axe-core in-page and keep only serious/critical violations. */
async function seriousViolations(page: Page): Promise<AxeResult['violations']> {
  await page.addScriptTag({ path: 'node_modules/axe-core/axe.min.js' });
  const result = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: () => Promise<AxeResult> } }).axe;
    return axe.run();
  });
  return result.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
}

async function signIn(page: Page): Promise<void> {
  await page.goto('/');
  await page.getByLabel('Email').fill('astronomer@snoodleboot.com');
  await page.getByLabel('Password').fill('supernova');
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page.getByText(/Aurora Platform · 4 components/)).toBeVisible();
}

// The P5 exit criterion made executable: login → scrub → cut, driven in a real browser against
// the in-browser MSW API (VITE_E2E_MOCK). Live-SSE is covered by the R3 unit/integration tests.
test('login → scrub the meridian → cut a release', async ({ page }) => {
  // Unauthenticated visitors are gated to the login screen.
  await page.goto('/');
  await expect(page).toHaveURL(/\/login$/);

  // Log in (the mock accepts any non-"wrong" password for an allowed email).
  await page.getByLabel('Email').fill('astronomer@snoodleboot.com');
  await page.getByLabel('Password').fill('supernova');
  await page.getByRole('button', { name: /sign in/i }).click();

  // The constellation loads for the seeded product.
  await expect(page.getByText(/Aurora Platform · 4 components/)).toBeVisible();

  // Scrub the meridian earlier with the keyboard; the tick readout moves.
  const meridian = page.getByRole('slider', { name: /release meridian/i });
  await meridian.focus();
  const before = await meridian.getAttribute('aria-valuenow');
  await page.keyboard.press('ArrowLeft');
  await expect(meridian).not.toHaveAttribute('aria-valuenow', before ?? '');

  // Return to "now" so every component is pinned, then cut a release.
  await page.keyboard.press('End');
  await page.getByRole('button', { name: /cut release/i }).click();

  // The new release (server-assigned product version 5.1.0) appears in the ledger.
  await expect(page.getByText(/5\.1\.0/).first()).toBeVisible();
});

// LAV-62: the impact highlight is reachable and legible with the keyboard alone.
test('keyboard-select a component and light its blast radius', async ({ page }) => {
  await signIn(page);

  const label = page.getByTestId('lane-label-comp-api');
  await label.focus();
  await page.keyboard.press('Enter');
  await expect(label).toHaveAttribute('aria-pressed', 'true');

  // ui and cli sit one hop from api, helm two — exactly one badge per impacted lane.
  const pinnedUi = page.getByTestId('station-comp-ui-v4');
  await expect(pinnedUi).toHaveAttribute('data-impact-level', 'minor');
  await expect(page.getByTestId('station-badge-comp-ui-v4')).toHaveText('▲ minor');
  await expect(page.getByTestId('station-comp-api-v4')).toHaveAttribute(
    'data-impact-state',
    'source',
  );
  await expect(page.getByTestId(/^station-badge-/)).toHaveCount(3);

  const violations = await seriousViolations(page);
  expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);

  // Escape clears the selection and every tint with it.
  await page.keyboard.press('Escape');
  await expect(label).toHaveAttribute('aria-pressed', 'false');
  await expect(pinnedUi).not.toHaveAttribute('data-impact-level', /.*/);
});
