// `bump_rationale` arrives as an opaque JSON *string* (contract §10), not prose. The server
// ships `{policy, product_bump, removed_any, components: {id: {own, effective}}}` — see
// app/queries/releases/cut_release_query.py. Shape it into one human line HERE and nowhere
// else, so the wire type stays `string | null` everywhere upstream.

interface RationaleComponent {
  readonly own?: unknown;
}

interface Rationale {
  readonly removed_any?: unknown;
  readonly components?: unknown;
  /** Honoured if the backend ever adds a ready-made human line. */
  readonly reason?: unknown;
}

function changedCount(entries: readonly unknown[]): number {
  return entries.filter(
    (entry) =>
      typeof entry === 'object' && entry !== null && (entry as RationaleComponent).own !== 'none',
  ).length;
}

/**
 * One readable line explaining a release's derived bump, or `null` when there is nothing to
 * say. Anything unparseable or unrecognised falls back to the raw string rather than being
 * dropped — a rationale we cannot shape is still better than silence.
 */
export function formatBumpRationale(raw: string | null | undefined): string | null {
  if (raw === null || raw === undefined) return null;
  const trimmed = raw.trim();
  if (trimmed.length === 0) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    return trimmed;
  }
  if (typeof parsed !== 'object' || parsed === null) return trimmed;

  const rationale = parsed as Rationale;
  if (typeof rationale.reason === 'string' && rationale.reason.trim().length > 0) {
    return rationale.reason.trim();
  }

  const { components } = rationale;
  if (typeof components !== 'object' || components === null) return trimmed;

  const entries = Object.values(components as Record<string, unknown>);
  if (entries.length === 0) return trimmed;

  const noun = entries.length === 1 ? 'component' : 'components';
  const head = `${changedCount(entries)} of ${entries.length} ${noun} changed`;
  return rationale.removed_any === true
    ? `${head}; a removed component forces a major.`
    : `${head}.`;
}
