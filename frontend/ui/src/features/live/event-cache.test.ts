import { describe, expect, it } from 'vitest';

import type {
  DependencyAddedEvent,
  DependencyRemovedEvent,
  VersionCreatedEvent,
  VersionRolledBackEvent,
} from '@/api';
import { SEED_PRODUCT_ID, seedComponents, seedDependencies, seedProduct } from '@/mocks';
import type { Dependency, GraphResponse, Timeline, Version } from '@/types';

import {
  applyDependencyAdded,
  applyDependencyRemoved,
  applyVersionCreated,
  applyVersionRolledBack,
} from './event-cache';

function buildTimeline(): Timeline {
  return { product: seedProduct(), components: seedComponents() };
}

describe('applyVersionCreated', () => {
  it('appends the version, marks it active, and demotes the previous active', () => {
    const timeline = buildTimeline();
    const incoming: Version = {
      id: 'comp-api-v5',
      component_id: 'comp-api',
      major: 2,
      minor: 5,
      patch: 0,
      prerelease: null,
      status: 'active',
      created_at: '2026-05-13T12:00:00.000Z',
    };
    const event: VersionCreatedEvent = { component_id: 'comp-api', version: incoming };

    const next = applyVersionCreated(timeline, event);
    const api = next.components.find((component) => component.id === 'comp-api');

    expect(api?.versions).toHaveLength(6);
    expect(api?.versions.at(-1)).toMatchObject({ id: 'comp-api-v5', status: 'active' });
    // Previously active 2.4.0 is now superseded.
    const prevActive = api?.versions.find((version) => version.id === 'comp-api-v4');
    expect(prevActive?.status).toBe('superseded');
    // Exactly one active version remains for that component.
    expect(api?.versions.filter((version) => version.status === 'active')).toHaveLength(1);
  });

  it('does not touch other components', () => {
    const timeline = buildTimeline();
    const event: VersionCreatedEvent = {
      component_id: 'comp-api',
      version: {
        id: 'comp-api-v5',
        component_id: 'comp-api',
        major: 2,
        minor: 5,
        patch: 0,
        prerelease: null,
        status: 'active',
        created_at: '2026-05-13T12:00:00.000Z',
      },
    };

    const next = applyVersionCreated(timeline, event);
    const ui = next.components.find((component) => component.id === 'comp-ui');

    expect(ui).toBe(timeline.components.find((component) => component.id === 'comp-ui'));
  });

  it('does not mutate the input timeline', () => {
    const timeline = buildTimeline();
    const before = structuredClone(timeline);
    const event: VersionCreatedEvent = {
      component_id: 'comp-api',
      version: {
        id: 'comp-api-v5',
        component_id: 'comp-api',
        major: 2,
        minor: 5,
        patch: 0,
        prerelease: null,
        status: 'active',
        created_at: '2026-05-13T12:00:00.000Z',
      },
    };

    const next = applyVersionCreated(timeline, event);

    expect(timeline).toEqual(before);
    expect(next).not.toBe(timeline);
    expect(next.components).not.toBe(timeline.components);
  });
});

describe('applyVersionRolledBack', () => {
  it('flips the rolled-back and reactivated statuses', () => {
    const timeline = buildTimeline();
    const event: VersionRolledBackEvent = {
      component_id: 'comp-api',
      version_id: 'comp-api-v4',
      reactivated_version_id: 'comp-api-v3',
    };

    const next = applyVersionRolledBack(timeline, event);
    const api = next.components.find((component) => component.id === 'comp-api');

    expect(api?.versions.find((version) => version.id === 'comp-api-v4')?.status).toBe(
      'rolled_back',
    );
    expect(api?.versions.find((version) => version.id === 'comp-api-v3')?.status).toBe('active');
  });

  it('does not mutate the input timeline', () => {
    const timeline = buildTimeline();
    const before = structuredClone(timeline);
    const event: VersionRolledBackEvent = {
      component_id: 'comp-api',
      version_id: 'comp-api-v4',
      reactivated_version_id: 'comp-api-v3',
    };

    const next = applyVersionRolledBack(timeline, event);

    expect(timeline).toEqual(before);
    expect(next).not.toBe(timeline);
  });
});

const NEW_EDGE: Dependency = {
  id: 'dep-cli-ui',
  product_id: SEED_PRODUCT_ID,
  from_component_id: 'comp-cli',
  to_component_id: 'comp-ui',
  created_at: '2026-05-13T12:00:00.000Z',
};

function buildGraph(): GraphResponse {
  return {
    product_id: SEED_PRODUCT_ID,
    nodes: seedComponents().map(({ id, product_id, name, kind }) => ({
      id,
      product_id,
      name,
      kind,
    })),
    edges: seedDependencies(),
  };
}

describe('applyDependencyAdded', () => {
  it('appends exactly one edge', () => {
    const graph = buildGraph();

    const next = applyDependencyAdded(graph, { dependency: NEW_EDGE });

    expect(next.edges).toHaveLength(graph.edges.length + 1);
    expect(next.edges.at(-1)).toEqual(NEW_EDGE);
  });

  it('ignores a duplicate id so a replayed frame never double-draws an arc', () => {
    const graph = buildGraph();
    const duplicate: DependencyAddedEvent = { dependency: graph.edges[0]! };

    const next = applyDependencyAdded(graph, duplicate);

    expect(next.edges).toHaveLength(graph.edges.length);
    expect(next).toBe(graph);
  });

  it('does not mutate the input graph', () => {
    const graph = buildGraph();
    const before = structuredClone(graph);

    const next = applyDependencyAdded(graph, { dependency: NEW_EDGE });

    expect(graph).toEqual(before);
    expect(next).not.toBe(graph);
    expect(next.edges).not.toBe(graph.edges);
  });
});

describe('applyDependencyRemoved', () => {
  it('removes only the matching edge', () => {
    const graph = buildGraph();
    const event: DependencyRemovedEvent = {
      dependency: {
        id: 'dep-ui-api',
        product_id: SEED_PRODUCT_ID,
        from_component_id: 'comp-ui',
        to_component_id: 'comp-api',
      },
    };

    const next = applyDependencyRemoved(graph, event);

    expect(next.edges.map((edge) => edge.id)).toEqual(['dep-cli-api', 'dep-helm-ui']);
  });

  it('is a no-op for an id the graph does not hold', () => {
    const graph = buildGraph();
    const event: DependencyRemovedEvent = {
      dependency: {
        id: 'dep-nope',
        product_id: SEED_PRODUCT_ID,
        from_component_id: 'comp-ui',
        to_component_id: 'comp-api',
      },
    };

    expect(applyDependencyRemoved(graph, event).edges).toHaveLength(graph.edges.length);
  });

  it('does not mutate the input graph', () => {
    const graph = buildGraph();
    const before = structuredClone(graph);
    const event: DependencyRemovedEvent = {
      dependency: {
        id: 'dep-ui-api',
        product_id: SEED_PRODUCT_ID,
        from_component_id: 'comp-ui',
        to_component_id: 'comp-api',
      },
    };

    const next = applyDependencyRemoved(graph, event);

    expect(graph).toEqual(before);
    expect(next).not.toBe(graph);
    expect(next.edges).not.toBe(graph.edges);
  });
});
