// Minimal EventSource stand-in for driving `useProductEvents` in tests via the
// injected `eventSourceFactory`. Only the surface `subscribeToProductEvents` touches
// is implemented: named-event listeners, `close`, and a manual `emit`.

type Listener = (event: MessageEvent) => void;

export class FakeEventSource {
  readonly url: string;
  closed = false;

  private readonly listeners = new Map<string, Set<Listener>>();

  constructor(url: string) {
    this.url = url;
  }

  addEventListener(type: string, listener: Listener): void {
    const set = this.listeners.get(type) ?? new Set<Listener>();
    set.add(listener);
    this.listeners.set(type, set);
  }

  removeEventListener(type: string, listener: Listener): void {
    this.listeners.get(type)?.delete(listener);
  }

  close(): void {
    this.closed = true;
  }

  /** Dispatch a named SSE event; `data` (if given) is JSON-encoded onto `event.data`. */
  emit(type: string, data?: unknown): void {
    this.emitRaw(type, data === undefined ? '' : JSON.stringify(data));
  }

  /** Dispatch a named SSE event with a verbatim `event.data` — for malformed-frame tests. */
  emitRaw(type: string, data: string): void {
    const event = { type, data } as MessageEvent;
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }
}
