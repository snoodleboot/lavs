import type { Dependency, Release, Version } from '@/types';

import { API_BASE } from './http';

// SSE payloads — docs/design/API_CONTRACT.md §6.
export interface VersionCreatedEvent {
  readonly component_id: string;
  readonly version: Version;
}

export interface VersionRolledBackEvent {
  readonly component_id: string;
  readonly version_id: string;
  readonly reactivated_version_id: string;
}

export interface ReleaseCutEvent {
  readonly release: Release;
}

export interface DependencyAddedEvent {
  readonly dependency: Dependency;
}

/** A removal only identifies the edge; the server omits `created_at` (contract §6). */
export interface DependencyRemovedEvent {
  readonly dependency: Pick<
    Dependency,
    'id' | 'product_id' | 'from_component_id' | 'to_component_id'
  >;
}

export interface ProductEventHandlers {
  readonly onVersionCreated?: (event: VersionCreatedEvent) => void;
  readonly onVersionRolledBack?: (event: VersionRolledBackEvent) => void;
  readonly onReleaseCut?: (event: ReleaseCutEvent) => void;
  readonly onDependencyAdded?: (event: DependencyAddedEvent) => void;
  readonly onDependencyRemoved?: (event: DependencyRemovedEvent) => void;
  readonly onError?: (error: Event) => void;
  readonly onOpen?: () => void;
}

export interface SubscribeOptions {
  /** Backoff ceiling for reconnect attempts (ms). */
  readonly maxBackoffMs?: number;
  /** Injectable for tests; defaults to the global EventSource. */
  readonly eventSourceFactory?: (url: string) => EventSource;
}

/** Live product stream. Returns a disposer that closes the connection and cancels reconnects. */
export function subscribeToProductEvents(
  productId: string,
  handlers: ProductEventHandlers,
  options: SubscribeOptions = {},
): () => void {
  const url = `${API_BASE}/products/${productId}/events`;
  const maxBackoff = options.maxBackoffMs ?? 30_000;
  const factory =
    options.eventSourceFactory ??
    ((target: string) => new EventSource(target, { withCredentials: true }));

  let source: EventSource | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let attempt = 0;
  let disposed = false;

  const parse = <T>(event: MessageEvent): T | null => {
    try {
      return JSON.parse(event.data as string) as T;
    } catch {
      return null;
    }
  };

  const connect = (): void => {
    if (disposed) return;
    source = factory(url);

    source.addEventListener('open', () => {
      attempt = 0;
      handlers.onOpen?.();
    });

    source.addEventListener('version.created', (event) => {
      const data = parse<VersionCreatedEvent>(event);
      if (data) handlers.onVersionCreated?.(data);
    });

    source.addEventListener('version.rolled_back', (event) => {
      const data = parse<VersionRolledBackEvent>(event);
      if (data) handlers.onVersionRolledBack?.(data);
    });

    source.addEventListener('release.cut', (event) => {
      const data = parse<ReleaseCutEvent>(event);
      if (data) handlers.onReleaseCut?.(data);
    });

    source.addEventListener('dependency.added', (event) => {
      const data = parse<DependencyAddedEvent>(event);
      if (data) handlers.onDependencyAdded?.(data);
    });

    source.addEventListener('dependency.removed', (event) => {
      const data = parse<DependencyRemovedEvent>(event);
      if (data) handlers.onDependencyRemoved?.(data);
    });

    source.addEventListener('error', (event) => {
      handlers.onError?.(event);
      // Browser EventSource auto-reconnects; do our own bounded backoff for robustness.
      source?.close();
      if (disposed) return;
      const delay = Math.min(maxBackoff, 1000 * 2 ** attempt);
      attempt += 1;
      reconnectTimer = setTimeout(connect, delay);
    });
  };

  connect();

  return (): void => {
    disposed = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    source?.close();
  };
}
