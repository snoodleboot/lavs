// Pure, immutable reducers that fold live SSE events into the timeline cache.
// Never mutate their inputs — TanStack Query relies on referential change to re-render.

import type {
  DependencyAddedEvent,
  DependencyRemovedEvent,
  VersionCreatedEvent,
  VersionRolledBackEvent,
} from '@/api';
import type { ComponentWithVersions, GraphResponse, Timeline, Version } from '@/types';

/**
 * Append the created version to its component, mark it `active`, and demote the
 * previously-active version to `superseded`. Returns a new `Timeline`; the input
 * (and every nested array/object it touches) is left untouched.
 */
export function applyVersionCreated(timeline: Timeline, event: VersionCreatedEvent): Timeline {
  const components = timeline.components.map((component) => {
    if (component.id !== event.component_id) return component;
    return addVersionToComponent(component, event.version);
  });

  return { ...timeline, components };
}

/**
 * Flip statuses for a rollback: the rolled-back version becomes `rolled_back` and
 * the re-activated version becomes `active`. Returns a new `Timeline`; inputs are
 * never mutated.
 */
export function applyVersionRolledBack(
  timeline: Timeline,
  event: VersionRolledBackEvent,
): Timeline {
  const components = timeline.components.map((component) => {
    const versions = component.versions.map((version) => {
      if (version.id === event.version_id) return { ...version, status: 'rolled_back' as const };
      if (version.id === event.reactivated_version_id) {
        return { ...version, status: 'active' as const };
      }
      return version;
    });

    return { ...component, versions };
  });

  return { ...timeline, components };
}

function addVersionToComponent(
  component: ComponentWithVersions,
  incoming: Version,
): ComponentWithVersions {
  const demoted = component.versions.map((version) =>
    version.status === 'active' ? { ...version, status: 'superseded' as const } : version,
  );

  const appended: Version = { ...incoming, status: 'active' };

  return { ...component, versions: [...demoted, appended] };
}

/**
 * Append a live dependency edge to the graph cache, ignoring a duplicate id (SSE frames can
 * arrive twice, and REST reconciliation must not double-draw an arc). Returns a new graph.
 */
export function applyDependencyAdded(
  graph: GraphResponse,
  event: DependencyAddedEvent,
): GraphResponse {
  if (graph.edges.some((edge) => edge.id === event.dependency.id)) return graph;
  return { ...graph, edges: [...graph.edges, event.dependency] };
}

/** Drop a removed dependency edge from the graph cache. Returns a new graph. */
export function applyDependencyRemoved(
  graph: GraphResponse,
  event: DependencyRemovedEvent,
): GraphResponse {
  return { ...graph, edges: graph.edges.filter((edge) => edge.id !== event.dependency.id) };
}
