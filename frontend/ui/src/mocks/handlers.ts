import { HttpResponse, http, type HttpHandler } from 'msw';

import type {
  ApiErrorCode,
  ChangeLevel,
  ImpactedComponent,
  Meta,
  Release,
  ReleaseComponent,
} from '@/types';

import { db } from './db';
import { SEED_BUMP_RATIONALE, seedChangeLevel, toComponent } from './fixtures';

const BASE = '*/api';

function errorResponse(status: number, code: ApiErrorCode, message: string): Response {
  return HttpResponse.json({ error: { code, message, details: null } }, { status });
}

function bumpProductVersion(): string {
  // Mirror the server default bump (minor) from a 5.0.0 base for the mock.
  const minor = db.releaseCounter + 1;
  db.releaseCounter = minor;
  return `5.${minor}.0`;
}

// Mirror of the server's contraction policy (app/domain/bump_propagation.py): a dependency's
// major is felt as a minor by its dependents, anything lesser as a patch.
function propagate(level: ChangeLevel): ChangeLevel {
  return level === 'major' ? 'minor' : 'patch';
}

/** Transitive dependents of `componentId`, each with its projected level (breadth-first). */
function impactedBy(componentId: string): ImpactedComponent[] {
  const impacted = new Map<string, ChangeLevel>();
  let frontier: readonly (readonly [string, ChangeLevel])[] = [[componentId, 'major']];

  while (frontier.length > 0) {
    const next: (readonly [string, ChangeLevel])[] = [];
    for (const [id, level] of frontier) {
      for (const edge of db.dependencies) {
        if (edge.to_component_id !== id) continue;
        const dependent = edge.from_component_id;
        if (dependent === componentId || impacted.has(dependent)) continue;
        const projected = propagate(level);
        impacted.set(dependent, projected);
        next.push([dependent, projected]);
      }
    }
    frontier = next;
  }

  return [...impacted].map(([id, projected_change_level]) => ({
    component_id: id,
    projected_change_level,
  }));
}

export const handlers: HttpHandler[] = [
  // --- meta / auth ---
  http.get(`${BASE}/meta`, () => {
    const meta: Meta = { edition: 'oss', auth_modes: ['password', 'apikey'] };
    return HttpResponse.json(meta);
  }),

  http.get(`${BASE}/auth/me`, () => {
    if (!db.principal) return errorResponse(401, 'unauthorized', 'Not authenticated');
    return HttpResponse.json(db.principal);
  }),

  http.post(`${BASE}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { email?: string; password?: string };
    if (!body.email || !body.password) {
      return errorResponse(422, 'validation_error', 'Email and password are required');
    }
    if (body.password === 'wrong') {
      return errorResponse(401, 'unauthorized', 'Invalid credentials');
    }
    db.principal = { kind: 'user', id: 'user-1', email: body.email, edition: 'oss' };
    return HttpResponse.json(db.principal);
  }),

  http.post(`${BASE}/auth/logout`, () => {
    db.principal = null;
    return new HttpResponse(null, { status: 204 });
  }),

  // --- products / timeline ---
  http.get(`${BASE}/products`, () => HttpResponse.json([db.product])),

  http.get(`${BASE}/products/:id`, ({ params }) => {
    if (params.id !== db.product.id) return errorResponse(404, 'not_found', 'Unknown product');
    return HttpResponse.json(db.product);
  }),

  http.get(`${BASE}/products/:id/timeline`, ({ params }) => {
    if (params.id !== db.product.id) return errorResponse(404, 'not_found', 'Unknown product');
    return HttpResponse.json({ product: db.product, components: db.components });
  }),

  http.get(`${BASE}/products/:id/components`, ({ params }) => {
    if (params.id !== db.product.id) return errorResponse(404, 'not_found', 'Unknown product');
    return HttpResponse.json(db.components.map(toComponent));
  }),

  // --- dependency graph / impact (P9, read-only in this scope) ---
  http.get(`${BASE}/products/:id/graph`, ({ params }) => {
    if (params.id !== db.product.id) return errorResponse(404, 'not_found', 'Unknown product');
    return HttpResponse.json({
      product_id: db.product.id,
      nodes: db.components.map(toComponent),
      edges: db.dependencies,
    });
  }),

  http.get(`${BASE}/products/:id/impact`, ({ params, request }) => {
    if (params.id !== db.product.id) return errorResponse(404, 'not_found', 'Unknown product');
    const componentId = new URL(request.url).searchParams.get('component') ?? '';
    if (!db.components.some((component) => component.id === componentId)) {
      return errorResponse(404, 'not_found', 'Unknown component');
    }
    return HttpResponse.json({ component_id: componentId, impacted: impactedBy(componentId) });
  }),

  http.get(`${BASE}/components/:id/versions`, ({ params }) => {
    const component = db.components.find((candidate) => candidate.id === params.id);
    if (!component) return errorResponse(404, 'not_found', 'Unknown component');
    return HttpResponse.json(component.versions);
  }),

  // --- releases ---
  http.get(`${BASE}/products/:id/releases`, ({ params }) => {
    if (params.id !== db.product.id) return errorResponse(404, 'not_found', 'Unknown product');
    return HttpResponse.json(db.releases);
  }),

  http.get(`${BASE}/releases/:id`, ({ params }) => {
    const release = db.releases.find((candidate) => candidate.id === params.id);
    if (!release) return errorResponse(404, 'not_found', 'Unknown release');
    return HttpResponse.json(release);
  }),

  http.post(`${BASE}/products/:id/releases`, async ({ params, request }) => {
    if (params.id !== db.product.id) return errorResponse(404, 'not_found', 'Unknown product');
    const body = (await request.json().catch(() => ({}))) as { label?: string };
    const components: ReleaseComponent[] = db.components
      .map((component): ReleaseComponent | null => {
        const active = component.versions.find((version) => version.status === 'active');
        if (!active) return null;
        return {
          component_id: component.id,
          name: component.name,
          version_id: active.id,
          version: `${active.major}.${active.minor}.${active.patch}`,
          change_level: seedChangeLevel(component.id),
        };
      })
      .filter((entry): entry is ReleaseComponent => entry !== null);

    const productVersion = bumpProductVersion();
    const release: Release = {
      id: `rel-${db.releaseCounter}`,
      product_id: db.product.id,
      product_version: productVersion,
      label: body.label ?? null,
      created_at: '2026-05-13T12:00:00.000Z',
      bump_level: 'minor',
      bump_rationale: SEED_BUMP_RATIONALE,
      components,
    };
    db.releases = [release, ...db.releases];
    return HttpResponse.json(release, { status: 201 });
  }),
];
