// Domain types — the exact shapes from docs/design/API_CONTRACT.md §3.
// The FE cannot assume anything not declared in the contract.

export type ComponentKind = 'library' | 'service' | 'ui' | 'cli';

export type VersionStatus = 'active' | 'superseded' | 'rolled_back';

export type AuthMode = 'password' | 'apikey';

export type PrincipalKind = 'user' | 'service';

export type Edition = 'oss' | 'ee';

/** P9 — how much a component changed against the prior manifest (contract §10). */
export type ChangeLevel = 'major' | 'minor' | 'patch';

/** P9 — a release's derived product bump; `none` when nothing changed. */
export type BumpLevel = ChangeLevel | 'none';

export interface Product {
  readonly id: string;
  readonly name: string;
  readonly description: string | null;
  readonly created_at: string;
}

export interface Component {
  readonly id: string;
  readonly product_id: string;
  readonly name: string;
  readonly kind: ComponentKind;
}

/** Immutable, append-only. `version` is derived from major.minor.patch(-prerelease). */
export interface Version {
  readonly id: string;
  readonly component_id: string;
  readonly major: number;
  readonly minor: number;
  readonly patch: number;
  readonly prerelease: string | null;
  readonly status: VersionStatus;
  readonly created_at: string;
}

/** One pinned component inside a frozen release manifest. */
export interface ReleaseComponent {
  readonly component_id: string;
  readonly name: string;
  readonly version_id: string;
  readonly version: string;
  /** P9: this component's own change vs the prior manifest (null under the legacy policy). */
  readonly change_level: ChangeLevel | null;
}

/** Frozen: pins exact version_ids, never changes after a cut. */
export interface Release {
  readonly id: string;
  readonly product_id: string;
  readonly product_version: string;
  readonly label: string | null;
  readonly created_at: string;
  /** P9: the derived product bump (null on pre-P9 rows). */
  readonly bump_level: BumpLevel | null;
  /** P9: JSON string explaining the derivation — shape it through `formatBumpRationale`. */
  readonly bump_rationale: string | null;
  readonly components: readonly ReleaseComponent[];
}

/** P9 — one intra-product dependency edge: `from` depends on `to`. */
export interface Dependency {
  readonly id: string;
  readonly product_id: string;
  readonly from_component_id: string;
  readonly to_component_id: string;
  readonly created_at: string;
}

/** P9 — the product's dependency DAG: GET /products/{id}/graph. */
export interface GraphResponse {
  readonly product_id: string;
  readonly nodes: readonly Component[];
  readonly edges: readonly Dependency[];
}

/** P9 — one transitive dependent surfaced by an impact query. */
export interface ImpactedComponent {
  readonly component_id: string;
  /** The backend never returns `none` here. */
  readonly projected_change_level: ChangeLevel;
}

/** P9 — the blast radius of a hypothetical major change: GET /products/{id}/impact. */
export interface Impact {
  readonly component_id: string;
  readonly impacted: readonly ImpactedComponent[];
}

/** A component with its full version history — the shape inside a timeline. */
export interface ComponentWithVersions extends Component {
  readonly versions: readonly Version[];
}

/** Composite response for the Constellation view (one call). */
export interface Timeline {
  readonly product: Product;
  readonly components: readonly ComponentWithVersions[];
}

/** Authenticated identity resolved by the backend. */
export interface Principal {
  readonly kind: PrincipalKind;
  readonly id: string;
  readonly email: string | null;
  readonly edition: Edition;
}

/** Deploy-config surface the UI reads to render the right login. */
export interface Meta {
  readonly edition: Edition;
  readonly auth_modes: readonly AuthMode[];
}
