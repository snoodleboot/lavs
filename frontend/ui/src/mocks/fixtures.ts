import type {
  ChangeLevel,
  Component,
  ComponentKind,
  ComponentWithVersions,
  Dependency,
  Principal,
  Product,
  Release,
  Version,
} from '@/types';

// Deterministic seed mirroring the Constellation mockup (Aurora Platform, 4 components).
// IDs are stable strings so tests can assert against them.

export const SEED_PRODUCT_ID = 'prod-aurora';

export const seedPrincipal: Principal = {
  kind: 'user',
  id: 'user-1',
  email: 'astronomer@snoodleboot.com',
  edition: 'oss',
};

interface VersionSpec {
  readonly version: string;
  readonly day: number;
}

function makeVersions(componentId: string, specs: readonly VersionSpec[]): Version[] {
  return specs.map((spec, index) => {
    const [major, minor, patch] = spec.version.split('.').map(Number);
    const isLatest = index === specs.length - 1;
    return {
      id: `${componentId}-v${index}`,
      component_id: componentId,
      major: major ?? 0,
      minor: minor ?? 0,
      patch: patch ?? 0,
      prerelease: null,
      status: isLatest ? 'active' : 'superseded',
      created_at: `2026-05-${String(spec.day).padStart(2, '0')}T12:00:00.000Z`,
    };
  });
}

interface ComponentSpec {
  readonly id: string;
  readonly name: string;
  readonly kind: ComponentKind;
  readonly versions: readonly VersionSpec[];
}

const COMPONENT_SPECS: readonly ComponentSpec[] = [
  {
    id: 'comp-api',
    name: 'lavs-api',
    kind: 'service',
    versions: [
      { version: '2.0.0', day: 1 },
      { version: '2.1.0', day: 3 },
      { version: '2.2.0', day: 5 },
      { version: '2.3.0', day: 8 },
      { version: '2.4.0', day: 11 },
    ],
  },
  {
    id: 'comp-ui',
    name: 'lavs-ui',
    kind: 'ui',
    versions: [
      { version: '1.7.0', day: 2 },
      { version: '1.8.0', day: 4 },
      { version: '1.9.0', day: 7 },
      { version: '1.9.1', day: 9 },
      { version: '1.9.2', day: 12 },
    ],
  },
  {
    id: 'comp-helm',
    name: 'lavs-helm',
    kind: 'library',
    versions: [
      { version: '0.4.0', day: 1 },
      { version: '0.5.0', day: 6 },
      { version: '0.7.0', day: 10 },
    ],
  },
  {
    id: 'comp-cli',
    name: 'lavs-cli',
    kind: 'cli',
    versions: [
      { version: '1.0.0', day: 3 },
      { version: '1.1.0', day: 8 },
    ],
  },
];

export function seedProduct(): Product {
  return {
    id: SEED_PRODUCT_ID,
    name: 'Aurora Platform',
    description: 'The reference product for the Constellation view.',
    created_at: '2026-05-01T00:00:00.000Z',
  };
}

export function seedComponents(): ComponentWithVersions[] {
  return COMPONENT_SPECS.map((spec) => ({
    id: spec.id,
    product_id: SEED_PRODUCT_ID,
    name: spec.name,
    kind: spec.kind,
    versions: makeVersions(spec.id, spec.versions),
  }));
}

export function toComponent(component: ComponentWithVersions): Component {
  return {
    id: component.id,
    product_id: component.product_id,
    name: component.name,
    kind: component.kind,
  };
}

export function seedReleases(): Release[] {
  return [];
}

interface DependencySpec {
  readonly id: string;
  readonly from: string;
  readonly to: string;
}

// "from depends on to": the UI, the CLI and the Helm chart all depend on the API.
const DEPENDENCY_SPECS: readonly DependencySpec[] = [
  { id: 'dep-ui-api', from: 'comp-ui', to: 'comp-api' },
  { id: 'dep-cli-api', from: 'comp-cli', to: 'comp-api' },
  { id: 'dep-helm-ui', from: 'comp-helm', to: 'comp-ui' },
];

export function seedDependencies(): Dependency[] {
  return DEPENDENCY_SPECS.map((spec) => ({
    id: spec.id,
    product_id: SEED_PRODUCT_ID,
    from_component_id: spec.from,
    to_component_id: spec.to,
    created_at: '2026-05-12T12:00:00.000Z',
  }));
}

/**
 * Deterministic per-component `change_level` for a mocked cut: the API moved a minor,
 * everything downstream is contracted to a patch (mirrors the server's propagation).
 */
export function seedChangeLevel(componentId: string): ChangeLevel | null {
  if (componentId === 'comp-api') return 'minor';
  if (componentId === 'comp-helm') return null;
  return 'patch';
}

/**
 * A realistic `bump_rationale` — the server ships an opaque JSON *string* of this exact
 * shape (app/queries/releases/cut_release_query.py), never prose.
 */
export const SEED_BUMP_RATIONALE: string = JSON.stringify({
  policy: 'default',
  product_bump: 'minor',
  removed_any: false,
  components: {
    'comp-api': { own: 'minor', effective: 'minor' },
    'comp-cli': { own: 'patch', effective: 'patch' },
    'comp-helm': { own: 'none', effective: 'patch' },
    'comp-ui': { own: 'patch', effective: 'patch' },
  },
});
