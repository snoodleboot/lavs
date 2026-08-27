# P9 Constellation Frontend — Implementation Plan (LAV-61 / 62 / 63)

Frontend tech-lead plan, finalized against review. Target: `frontend/ui` (TypeScript 6 / React / pnpm / vitest / Playwright+axe). The P9 backend is **shipped and merged**; this plan **consumes the contract only** (`docs/design/API_CONTRACT.md §10`) and touches no server, migration, schema, or API code — see the closing note.

Three issues, one shared foundation:

- **LAV-61 (F1)** — Constellation dependency **edge layer**, fed by `GET /products/{id}/graph`.
- **LAV-62 (F2)** — **Impact highlight**, fed by `GET /products/{id}/impact?component=X`.
- **LAV-63 (F3)** — **Derived-bump readout** + per-component `change_level` + dependency SSE.

Two correctness themes drive the changes made during review, and they recur below:

1. **Release-frozen data is version-scoped, not component-scoped.** `change_level` belongs to a specific `version_id`; the meridian scrubs through time, so a station is only correctly labeled when its *pinned version* matches the release-frozen version. All `change_level` joins key on `version_id`.
2. **The bump badge and per-version tints must not smear across history.** The `bump_level` badge belongs to the latest *cut* release, so it is shown only when the meridian sits at "now"; impact/change-level badges attach to the **single pinned station** per lane, never to every historical version node.

---

## 0. Foundation (types + api client + mocks)

Atomic prep layer that F1/F2/F3 all import. If staged, it lands **inside F1's PR**; F2/F3 must never redefine the level unions or the `--patch` token.

### 0.1 Types — `src/types/domain.ts` (+ barrel `src/types/index.ts`)

`src/types/domain.ts` is coverage-excluded (declaration-only); tests attach to the consuming code, not the type file.

```ts
export type ChangeLevel = 'major' | 'minor' | 'patch';
export type BumpLevel = ChangeLevel | 'none';

export interface Dependency {
  readonly id: string;
  readonly product_id: string;
  readonly from_component_id: string;
  readonly to_component_id: string;
  readonly created_at: string;
}
export interface GraphResponse {
  readonly product_id: string;
  readonly nodes: readonly Component[];
  readonly edges: readonly Dependency[];
}
export interface ImpactedComponent {
  readonly component_id: string;
  readonly projected_change_level: ChangeLevel; // backend never returns 'none' here
}
export interface Impact {
  readonly component_id: string;
  readonly impacted: readonly ImpactedComponent[];
}
```

Extend existing shapes (contract §10):

- `Release` — add `readonly bump_level: BumpLevel | null;` and `readonly bump_rationale: string | null;` (`bump_rationale` is a **JSON string** on the wire, per §10 line 29 — see the format seam in F3(a); the wire type stays `string | null`).
- `ReleaseComponent` — add `readonly change_level: ChangeLevel | null;`. (`version_id` already exists on this shape — `reopen()` reads `component.version_id` — and is the join key for pinned stations.)

Re-export `ChangeLevel, BumpLevel, Dependency, GraphResponse, ImpactedComponent, Impact` from `src/types/index.ts`.

> Because `ReleaseCutEvent.release` in `src/api/events.ts` is already a domain `Release`, `bump_level`/`bump_rationale` ride the existing `release.cut` frame with **no** `events.ts` change for those fields.

### 0.2 API modules (read-only)

The three issues **only read** `/graph` and `/impact` and consume the `dependency.*` SSE. No screen creates or deletes a dependency, so the create/delete client surface is **out of scope** (see Open decisions). The shared `http` client already exposes `get`/`post`; **no `http.del` is added**.

- **ADD `src/api/graph.ts`** — `getGraph(productId, signal) => http.get<GraphResponse>(\`/products/${productId}/graph\`, { signal })`.
- **ADD `src/api/impact.ts`** — `getImpact(productId, componentId, signal) => http.get<Impact>(\`/products/${productId}/impact?component=${encodeURIComponent(componentId)}\`, { signal })`.
- **CHANGE `src/api/index.ts`** — re-export `getGraph`, `getImpact`, and (F3) the two new SSE event types.

Both mirror `src/api/products.ts` → `Promise<Result<T>>`; `STATUS_TO_CODE` already maps 404→`'not_found'`. Extend the shared client — do not hand-roll a fetch — so Result/error mapping stays uniform.

### 0.3 Query keys — `src/lib/query-keys.ts`

```ts
graph: (productId: string) => ['products', productId, 'graph'] as const,
impact: (productId: string, componentId: string) =>
  ['products', productId, 'impact', componentId] as const,
```

Both under the `['products', id, …]` prefix so SSE handlers and query hooks target identical entries.

### 0.4 Tokens — `src/styles/tokens.css`

`--danger #ff6b81` (major) and `--warn #ffd166` (minor) exist. Patch slate **#9fb0cc has no token** — the nearest (`--muted #7c89a6`, label literal `#9fb0d6`) are **not** the approved value. Add a real token rather than substituting or inlining:

```css
--patch: #9fb0cc;
```

`none`/`null` → no token, no tint, no badge.

### 0.5 Mocks (read-only handlers)

Because `onUnhandledRequest: 'error'`, all fetched routes need a handler before any app fetch.

- **`src/mocks/db.ts`** — extend `MockDb` with `dependencies: Dependency[]`; seed in `freshDb()`.
- **`src/mocks/fixtures.ts`** — add `seedDependencies()` returning stable-id `Dependency[]` over the existing 4 comps (e.g. `dep-ui-api`: comp-ui → comp-api, `dep-cli-api`, `dep-helm-api`). Add deterministic `change_level` to seeded release components and `bump_level` + a realistic **JSON-string** `bump_rationale` (e.g. `'{"reason":"api minor propagated to ui","from":"minor"}'`) to seeded releases.
- **`src/mocks/handlers.ts`** — add exactly two routes (detailed per issue), using `errorResponse` and the `params.id !== db.product.id → 404` guard:
  - `http.get` `*/api/products/:id/graph`
  - `http.get` `*/api/products/:id/impact`

No POST/DELETE dependency handlers are added in this scope. `server.ts` and `vitest.setup.ts` need no change (handlers auto-register; `resetDb()` runs per `afterEach`).

---

## F1 — LAV-61 · Dependency edge layer

A quiet left-gutter "spine": arcs between component **labels** (not versions), muted at rest, painted **before** the Streams group so station nodes sit on top. Arrowhead at the dependency ("from depends on to").

### Files to ADD
- **`src/features/constellation/use-graph.ts`** — `useGraph(productId)`, mirroring `use-timeline.ts`:
  ```ts
  useQuery({
    queryKey: queryKeys.graph(productId ?? 'none'),
    queryFn: ({ signal }) => unwrap(getGraph(productId ?? '', signal)),
    enabled: Boolean(productId),
  })
  ```
- **`src/features/constellation/dependency-edges.tsx`** — the `<g>` layer (geometry below).
- Tests: `use-graph.test.tsx`, `dependency-edges.test.tsx`.

### Files to CHANGE
- **`src/features/constellation/constellation-view.tsx`** — add `dependencies?: readonly Dependency[]` (default `[]`); insert `<DependencyEdges …/>` as a sibling `<g>` **between the `now` `<text>` (line 149) and the `timeline.components.map(<Stream/>)` block (line 151)** so it paints first.
- **`src/features/constellation/index.ts`** — export `useGraph`, `DependencyEdges`.
- **`src/pages/constellation-workspace.tsx`** — `const graph = useGraph(productId)`; pass `dependencies={graph.data?.edges ?? []}` into `<ConstellationView>` (beside `freshVersionIds`, lines 119-120).
- **`src/features/constellation/constellation-view.module.css`** — add `.edgeLayer`, `.dependencyEdge` (muted), `.dependencyEdgeActive` (brightened, used by F2). Reserve the label column (below). Any transition collapses in the existing `prefers-reduced-motion` @media block (lines 128-136).

### Reserved label gutter (resolves the geometry/overlap contradiction)
The approved "clear gutter" look requires a genuinely label-free band for the arcs. Lane labels render `textAnchor="end"` at x≈104 and extend **leftward**, so there is no free space at x 20–104 by default. Fix it deterministically:

- Introduce `LABEL_COLUMN` constants: cap the lane-label render width via CSS (`.laneLabel { max-inline-size: …; text-overflow: ellipsis }`) so labels never extend past `xLabelLeft = VIEWBOX.padLeft - LABEL_WIDTH`.
- Route **all** arc geometry to the left of `xLabelLeft`. This makes "arcs never overlap label glyphs" a true, testable guarantee rather than an aspiration.

### Geometry (exact) — `dependency-edges.tsx`
Reuse `geometry.ts` (`VIEWBOX`, `yOf`, `LANE_TOP`, `laneHeight`). **Do not** use per-version `xOf` — edges connect components.

1. Build a lane-index map from the **authoritative lane order** (`timeline.components`, not `graph.nodes`): `const indexOf = new Map(components.map((c, i) => [c.id, i]))`.
2. For each `dependency`, resolve `fromIndex`/`toIndex`; **skip** an edge whose endpoint id is absent from the timeline (defensive branch → dedicated test).
3. Endpoints anchor at the gutter's right edge: `xAnchor = xLabelLeft` (left of every label glyph); `yFrom = yOf(fromIndex, laneCount)`, `yTo = yOf(toIndex, laneCount)`.
4. Arc **bows left into the reserved gutter**: cubic/quadratic path, control point `xCtrl = xLabelLeft - depth`, `depth = 12 + Math.min(36, Math.abs(yFrom - yTo) * 0.25)`, clamped so `xCtrl` stays ≥ `VIEWBOX.padLeft - LABEL_WIDTH - GUTTER_DEPTH` (inside the reserved band).
5. **Arrowhead at the TO (dependency) endpoint** — small triangle `<path>` oriented rightward toward the label, head at `to`.
6. Each edge is `<path data-testid={\`dependency-edge-${dependency.id}\`} className={styles.dependencyEdge}>` — **distinct** from the intra-lane `connector-${component.id}` in `stream.tsx`. Stroke uses `var(--line)`/`var(--muted)` at low opacity (a "quiet spine"), **not** the per-component hue.
7. Wrap the layer in `<g data-testid="dependency-edges" className={styles.edgeLayer}>`. Paths are non-interactive at rest (`pointer-events: none`) so they never collide with the meridian scrub pointer capture.

### Data flow
`workspace [useGraph] → ConstellationView (dependencies prop) → DependencyEdges (indexOf from timeline.components, geometry from geometry.ts)`. `GET /graph` is the sole source; the layer is decorative.

### Tests (fails-without-fix)
- `use-graph.test.tsx` — `renderHook(useGraph)` with the MSW graph handler; `data.edges.length === seeded count`; `enabled:false` / no fetch when `productId` undefined (negative assertion, mirroring `use-product-events`).
- `dependency-edges.test.tsx` (bare `render`, hand-built `makeTimeline()` + fixed deps):
  - exactly N `dependency-edge-${id}` paths for N edges; **zero** when `dependencies=[]`.
  - an edge referencing an unknown component id renders nothing (branch for step 2).
  - endpoint math: assert the path's `d` starts/ends at `xAnchor` and `yOf(fromIndex)`/`yOf(toIndex)` (exact numbers).
  - **all geometry x-values ≤ `xLabelLeft`** (the clear-gutter guarantee).
  - arrowhead element present at the `to` endpoint.
- `constellation-view.test.tsx` — `dependency-edges` `<g>` appears **before** the first `stream-${id}` `<g>` in DOM order (paint-order guarantee).
- MSW: graph handler returns 404 for unknown product (assert via a `getGraph` error test).
- a11y: edges are decorative (`aria-hidden`/no role); axe clean on the constellation route.

### Acceptance
- `GET /products/{id}/graph` drives a muted arc per dependency in the reserved left gutter, arrowhead at the dependency, arcs beneath stations and meridian.
- No arc overlaps a lane-label glyph; no edge drawn for an id missing from `timeline.components`.
- Testids `dependency-edge-${id}` + layer `dependency-edges`, distinct from `connector-*`.
- Coverage L80/B70/F90/S85 held for the two new files; zero serious/critical axe.

---

## F2 — LAV-62 · Impact highlight

Selecting a component lights its blast radius: dependents tinted by `projected_change_level`, source gets a dashed ring, everything else dims, relevant edges brighten. **Impact keys on COMPONENT id** — never conflated with the version-id `freshVersionIds` space — and paints on **one node per lane** (the pinned station), never every historical version.

### Files to ADD
- **`src/features/constellation/use-impact.ts`**:
  ```ts
  useQuery({
    queryKey: queryKeys.impact(productId ?? 'none', componentId ?? 'none'),
    queryFn: ({ signal }) => unwrap(getImpact(productId ?? '', componentId ?? '', signal)),
    enabled: Boolean(productId && componentId), // fires only on selection
    staleTime: 30_000,                          // no refetch churn while hovering
  })
  ```
- Tests: `use-impact.test.tsx`.

### Files to CHANGE
- **`src/pages/constellation-workspace.tsx`**
  - `const [selectedComponentId, setSelectedComponentId] = useState<string | null>(null)` — the `key={productId}` remount in `constellation-page.tsx` (line 26) auto-clears on product switch.
  - `const impact = useImpact(productId, selectedComponentId)`.
  - Derive off `selectedComponentId`, **not** query presence, so clearing selection stops tinting even if the cache lingers: `impactedByComponent = new Map(impact.data?.impacted.map(i => [i.component_id, i.projected_change_level]) ?? [])`.
  - Thread `selectedComponentId`, `impactedByComponent`, `onSelectComponent={setSelectedComponentId}` into `<ConstellationView>`.
- **`src/features/constellation/constellation-view.tsx`**
  - Props (default empty, like `EMPTY_IDS`): `selectedComponentId?: string | null`, `impactedByComponent?: ReadonlyMap<string, ChangeLevel>`, `onSelectComponent?: (id: string | null) => void`.
  - **Resolve per component at the view level** (mirror `pinnedByComponent`, lines 43-45), then forward state to **the pinned station only**:
    - `selected = component.id === selectedComponentId`
    - `impactLevel = impactedByComponent.get(component.id) ?? null`
    - `dimmed = selectedComponentId !== null && !selected && impactLevel === null`
    - `impactState = selected ? 'source' : impactLevel !== null ? 'impacted' : dimmed ? 'dimmed' : undefined`
    - pass these **scalars** to `<Stream>`, which applies `impactState`/`impactLevel` **exclusively to the station whose version id equals `pinnedVersionId`** — exactly one badge + one aria annotation per impacted lane. Non-pinned/historical stations receive no impact state.
  - **Selection trigger (keyboard-first, a11y):** replace each lane `<text className={styles.laneLabel}>` (lines 129-137) with a focusable toggle — `role="button"`, `tabIndex={0}`, **`aria-pressed={component.id === selectedComponentId}`**, accessible name = component name, `onClick`/`onKeyDown` Enter/Space → `onSelectComponent(component.id)` (toggle off if already selected), visible focus ring. `aria-pressed` exposes the on/off state programmatically so selection is never color-only.
  - **Clear:** `Escape` handler on the SVG group (sibling to `handleKeyDown`, lines 47-61) → `onSelectComponent(null)`.
  - Pass `selectedComponentId`/`impactedByComponent` into `<DependencyEdges>` so edges touching the source/impacted set get `.dependencyEdgeActive`.
  - **Pointer-capture caveat:** the label toggle sits outside the 28px meridian grab zone; `stopPropagation` on it so a click never starts a scrub.
- **`src/features/constellation/stream.tsx`** — `StreamProps` gains `impactState?: 'source' | 'impacted' | 'dimmed'`, `impactLevel?: ChangeLevel | null`; apply these to the `<g data-testid="stream-…">` and forward **only to the pinned station**.
- **`src/features/constellation/station.tsx`** — extend `StationProps` with `impactState?: 'source' | 'impacted' | 'dimmed'` and `impactLevel?: ChangeLevel | null`:
  - push `styles.stationSource` (dashed ring) / `styles.stationImpacted` (change-level tint) / `styles.stationDimmed` (opacity) into the className array (lines 26-34).
  - render a **▲ glyph + text badge** at the `cy-13` badge slot for `impactLevel` (color never the only signal).
  - extend `aria-label` (line 36) — e.g. `… (impact: minor)` / `… (source)`.
  - emit `data-impact-state` / `data-impact-level` mirrors (asserted without reading fill).
- **`constellation-view.module.css`** — `.stationSource`, `.stationImpacted`, `.stationDimmed`, `.dependencyEdgeActive`.

### Badge-slot precedence (impact vs. F3 change_level)
Both the F2 impact badge and the F3 `change_level` badge target the `cy-13` slot on the pinned station. Precedence is explicit: **while a selection is active (`selectedComponentId !== null`), the impact badge owns the slot and the change_level badge is suppressed** on that station; with no active selection, the change_level badge shows. A test exercises a pinned **and** impacted station to prove the impact badge wins and the change_level badge is hidden.

### Reduced motion (JS seam, so the unit test can fail-without-fix)
jsdom does not evaluate `@media (prefers-reduced-motion)`, so a CSS-only collapse is untestable at the unit level. Gate the new glow/pulse through the existing **`useReducedMotion` JS seam**: toggle a `styles.animated` class in TSX (`!reducedMotion && styles.animated`). The unit test stubs `matchMedia({ matches: true })` and asserts the animated class is **absent** on source/impacted stations; a Playwright pass with `reducedMotion: 'reduce'` covers the rendered end state.

### Data flow
`workspace [selectedComponentId + useImpact] → ConstellationView (resolves scalars per component, targets the pinned station) → Stream → Station (tint + ▲ badge + dashed ring + dim)`; edges brightened in `DependencyEdges`. REST `/impact` is the only impact source; UI is driven off `selectedComponentId`.

### Tests (fails-without-fix)
- `use-impact.test.tsx` — `enabled:false` / no fetch when `componentId` null; on selection returns the seeded impacted set; key is `queryKeys.impact(id, comp)`.
- `station.test.tsx` — `impactState='source'` → `data-impact-state="source"` + dashed-ring class + aria-label contains "source"; `impactState='impacted'` + `impactLevel='minor'` → tint class + ▲ badge text "minor" + `data-impact-level="minor"`; `dimmed` → dim class. Assert text/attrs, not fill.
- `constellation-view.test.tsx` —
  - lane label carries `aria-pressed` reflecting selection; click **and** Enter/Space call `onSelectComponent(id)`; Escape calls `onSelectComponent(null)`; re-select toggles off.
  - with a `selectedComponentId` + impacted map: exactly the **pinned** stations of impacted lanes carry `data-impact-level`; non-pinned/historical version nodes in the same lane carry **none** (guards against per-version smear); source pinned station carries `data-impact-state="source"`; others `dimmed`; matching edges get `dependencyEdgeActive`.
  - branch tests for `dimmed` vs `impacted` vs `source`.
- Reduced-motion: `matchMedia({matches:true})` → animated class absent on source/impacted (JS seam).
- **Playwright** (`tests/e2e/constellation.spec.ts`, in-browser MSW): keyboard-focus a lane label, press Enter, assert exactly one dependent station shows `data-impact-level` + ▲ badge text; axe → zero serious/critical (focusable labels + dim state hold AA contrast, `aria-pressed` present).

### Acceptance
- Selecting a component (mouse or keyboard) fetches `/impact` and lights dependents on their **pinned station only**, tinted by projected level (major=`--danger`, minor=`--warn`, patch=`--patch`) with a ▲ glyph + text; source gets a dashed ring; others dim; touching edges brighten.
- The lane-label toggle exposes `aria-pressed`; selection is never color-only.
- Exactly one impact badge/aria annotation per impacted lane — no per-version duplication.
- Escape / re-select / product-switch clears selection and all tinting; selection never triggers a meridian scrub.
- Coverage + zero serious/critical axe held.

---

## F3 — LAV-63 · Derived-bump readout + per-component change_level + dependency SSE

Three parts: (a) product-version readout gains a `bump_level` badge + one-line `bump_rationale`; (b) pinned stations show the pinned version's own `change_level`; (c) `dependency.added`/`dependency.removed` SSE re-syncing the graph cache, REST `/graph` authoritative.

### (a) Derived-bump readout

**Design decision (resolved).** There is no derived/uncut-bump endpoint and the backend is frozen; `bump_level`/`bump_rationale` live on the **Release** model. The badge is sourced from the **latest cut release** (`releasesQuery.data?.[0]`) and stays live because `release.cut` prepends the enriched `Release` into `queryKeys.releases` (existing path, unchanged).

**Position gate (resolves the "card disagrees with itself" conflict).** The readout card's product version is scrub-derived (`derivedProductVersion(base, pinnedCount>0)`), while the bump is static from the latest release. Rendering both unconditionally lets one card say "unchanged from base" (at origin) while the badge reads "major". **Render the bump badge + rationale only when the derived readout reflects that release** — i.e. `pinnedCount > 0 && position === axis.maxTick` (meridian at "now"). Off "now" the badge is hidden; the card then shows only the scrubbed derived version, with no contradictory bump. Label the badge as the latest **cut** release's bump.

**`bump_rationale` is a JSON string, not prose (contract §10 line 29).** Rendering it raw would print `{"reason":…}`. Add a format seam:

- **ADD `src/features/releases/bump-rationale.ts`** — `formatBumpRationale(raw: string | null): string | null` that `JSON.parse`es the string, extracts the human field the backend populates (confirm against the shipped fixture/payload — e.g. `reason`), and returns it; on parse failure or unknown shape, returns a defensive fallback (the trimmed raw string, or `null`). Wire type stays `string | null`; shaping happens at this boundary only.
- Test `bump-rationale.test.ts` with a **realistic JSON string** (from the fixture), plus malformed-JSON and `null` branches.

Changes:
- **CHANGE `src/features/releases/product-version-readout.tsx`** — add props `bumpLevel?: BumpLevel | null`, `bumpRationale?: string | null`, `atNow?: boolean`. When `atNow && bumpLevel && bumpLevel !== 'none'`, render a bump badge (token color + ▲ + text, e.g. "▲ major") in `.head` beside `data-testid="meridian-tick"`, and one line `formatBumpRationale(bumpRationale)` beneath the `.pv` block. `none`/`null`/not-at-now → no badge, no rationale. New testids `bump-level` / `bump-rationale`.
- **CHANGE `src/pages/constellation-workspace.tsx`** — pass `bumpLevel={releasesQuery.data?.[0]?.bump_level}`, `bumpRationale={releasesQuery.data?.[0]?.bump_rationale}`, `atNow={position === axis.maxTick}` into `<ProductVersionReadout>` (line 129); `data?.[0]` is already read for `product_version`.

### (b) Per-component change_level on pinned stations — **keyed by version_id**

**Correctness (resolved).** `change_level` is version-scoped: a `ReleaseComponent` carries both `version_id` and `change_level`. The pinned station is whichever version the meridian sits on (`pinnedByComponent` from `deriveManifest`), so joining by `component_id` would paint the **latest** release's `change_level` onto a scrubbed-back historical version. Join by `version_id` instead, and show the badge only when the pinned version is part of the latest release.

- **CHANGE `src/pages/constellation-workspace.tsx`**:
  ```ts
  const changeLevelByVersion = new Map(
    releasesQuery.data?.[0]?.components.map(c => [c.version_id, c.change_level]) ?? []
  );
  ```
  thread as `changeLevelByVersion?: ReadonlyMap<string, ChangeLevel | null>` into `<ConstellationView>`.
- **CHANGE `constellation-view.tsx` → `stream.tsx` → `station.tsx`** — resolve at view level from the **pinned version id**: `changeLevel = pinnedVersionId ? (changeLevelByVersion.get(pinnedVersionId) ?? null) : null`. A **pinned** station renders the ▲ change-level badge (reusing the F2 badge slot/token), **suppressed while a selection is active** per the F2 precedence rule. A pinned version not in the latest release → `null` → no badge.
- `src/features/releases/frozen-manifest.ts` is **not** changed — the workspace sources the map directly from `releasesQuery.data[0].components`, so no frozen-manifest widening is needed.
- The **release ledger is out of scope** (see Open decisions) — no `release-ledger.tsx` change.

### (c) Dependency SSE (REST `/graph` is source of truth)

- **CHANGE `src/api/events.ts`** — add:
  ```ts
  export interface DependencyAddedEvent { dependency: Dependency }
  export interface DependencyRemovedEvent {
    dependency: Pick<Dependency,'id'|'product_id'|'from_component_id'|'to_component_id'>
  }
  ```
  add `onDependencyAdded?`/`onDependencyRemoved?` to `ProductEventHandlers`; add two `source.addEventListener('dependency.added'|'dependency.removed', …)` blocks in `connect()`, each `parse<T>()`-guarded exactly like the `version.created` block (lines 70-83). Re-export both event types from `src/api/index.ts`. **No** listener for bump — it rides `release.cut`.
- **ADD reducers in `src/features/live/event-cache.ts`** — pure, no-mutate, folding the **GRAPH** cache (not Timeline):
  ```ts
  applyDependencyAdded(graph: GraphResponse, e: DependencyAddedEvent): GraphResponse
    // { ...graph, edges: dedupeById([...graph.edges, e.dependency]) }
  applyDependencyRemoved(graph, e): GraphResponse
    // { ...graph, edges: graph.edges.filter(x => x.id !== e.dependency.id) }
  ```
  Export from `src/features/live/index.ts`.
- **CHANGE `src/features/live/use-product-events.ts`** — in the handler bag, mirror `onVersionCreated` (lines 86-93): optimistic `queryClient.setQueryData(queryKeys.graph(productId), prev => prev ? applyDependencyX(prev, event) : prev)` **then** `void queryClient.invalidateQueries({ queryKey: queryKeys.graph(productId) })`. A dropped/duplicate frame re-syncs on the next `GET /graph`. Follow the existing **ref pattern** (subscription created once per `productId`; read live values via refs) — no stale closures.

### Data flow
- Readout/pinned change_level: `releasesQuery.data?.[0]` (kept live by `release.cut`) → workspace maps (`bump_level`/`bump_rationale` for the readout, `change_level` **by version_id** for stations) → readout badge (gated to "now") + pinned-station badge.
- Dependency SSE: `dependency.*` frame → optimistic graph-cache reducer → invalidate `queryKeys.graph` → REST reconciles. **SSE never authoritative.**

### Tests (fails-without-fix)
- `event-cache.test.ts` — `applyDependencyAdded` appends exactly one edge and dedupes a duplicate id (exact count); `applyDependencyRemoved` removes only the matching id; immutability proof (`structuredClone` equality of input, `next !== graph`, `next.edges !== graph.edges`).
- `use-product-events.test.tsx` — `renderHook` + injected `FakeEventSource`; `act(() => fake.emit('dependency.added', { dependency }))` → `client.getQueryData(queryKeys.graph(id))` gained the edge **and** `invalidateQueries` called on the graph key; `dependency.removed` drops it; malformed JSON frame is a no-op; no-op when `productId` undefined.
- `bump-rationale.test.ts` — realistic JSON string → extracted human line; malformed JSON → fallback; `null` → `null`.
- `product-version-readout.test.tsx` — `atNow` + `bumpLevel='minor'` → `bump-level` text "minor" + ▲ + token class, `bump-rationale` line is the **formatted** value (not raw JSON); `atNow` false → **no** badge even with a level (position-gate branch); `bumpLevel='none'`/`null` → no badge. Assert text/attrs, not color.
- `station.test.tsx` — pinned station whose `pinnedVersionId` **is** in the release map with `change_level='patch'` → ▲ "patch" badge + `--patch` token class + `data-change-level`; pinned version **not** in the release map → **no** badge (version-scoped correctness); pinned **and** impacted during a selection → impact badge wins, change_level badge suppressed.
- MSW: graph + impact handlers return 404 for unknown product (assert via `getGraph`/`getImpact` error tests).
- a11y: readout badge and pinned change_level badges keep ▲+text; reduced-motion (JS seam) collapses any badge glow.
- SSE is intentionally **not** e2e-tested (not reliably mockable in a service worker) — hook/reducer unit tests are the coverage, per the existing convention.

### Acceptance
- Readout shows a `bump_level` badge (major/minor/patch; none/null → hidden) + one-line **formatted** rationale, **only when the meridian is at "now"** and sourced from the latest cut release; scrubbing away hides it so the card never contradicts itself.
- Pinned stations show the **pinned version's** `change_level` (▲ + text + token color), joined by `version_id`; a version not in the latest release shows nothing; a selection's impact badge takes precedence over the change_level badge.
- `dependency.added`/`dependency.removed` optimistically patch the graph cache then invalidate; a dropped frame re-syncs from `GET /graph`.
- Color never the only signal; coverage + axe held.

---

## PR shape

**Recommended: staged F1 → F2 → F3, with the §0 foundation folded into F1.** F1 (graph query + edge `<g>` + shared types/tokens/query-keys/read-only mocks) is self-contained and testable alone; F2 builds on F1's component-id→lane map, the pinned-station badge slot, and the `ChangeLevel` union; F3 reuses F2's badge slot/token seam and precedence rule. Staging keeps each PR inside coverage + axe review scope.

A single combined "P9 frontend" PR is also buildable and keeps the shared type-and-prop-chain widening atomic — its only real upside; choose it only if the team prefers one review. Either way, **define `ChangeLevel`/`BumpLevel` + `--patch` once in F1** so F2/F3 never redefine them.

## Testing & coverage
- Coverage gates enforced in `vite.config.ts`: **lines 80 / branches 70 / functions 90 / statements 85**, held per new file. Every new `.ts`/`.tsx` carries meaningful tests; every new test must **fail without its fix** — the reduced-motion assertion runs through the `useReducedMotion` JS seam (not a jsdom-inert CSS `@media`), and MSW error branches assert real 404 `err` codes.
- Playwright + axe: **zero serious/critical** violations on the constellation route. Color is never the only signal (▲ glyph + text on every tinted badge; `aria-pressed` on the lane-label toggle). `use-reduced-motion` collapses glow/pulse.
- REST `GET /graph` is the source of truth; `dependency.*` SSE frames are best-effort — a dropped frame re-syncs via REST, mirroring `version.created`.

## Open decisions (deliberate deferrals)
- **Dependency create/delete API is out of scope.** LAV-61/62/63 only read `/graph`, read `/impact`, and consume `dependency.*` SSE + REST re-sync; no screen mutates dependencies. `src/api/dependencies.ts`, `http.del`, and the POST/DELETE MSW handlers + 201/204/409/404 test matrix are **cut** and belong to a future dependency-editor issue — carrying them now would be coverage-bearing dead product code. The SSE-consume path (reducers + graph invalidation) stands on its own.
- **Release-ledger `change_level` is out of scope.** The signed-off mockup scopes `change_level` display to the readout badge and **pinned stations** only. Rendering per-component change_level in `release-ledger.tsx` (and the `frozen-manifest.ts` widening) is extra UI surface + branches + axe burden not in the approved design; deferred pending explicit sign-off.
- **CommandPalette "Select/Clear component" actions dropped as redundant.** The focusable lane-label toggle (Enter/Space to select, Escape to clear, `aria-pressed`) already delivers a complete pure-keyboard path; a palette pair would add surface and tests without an a11y gain. Revisit only if discoverability (not access) is raised as a separate goal.

## No backend changes
This plan adds only frontend code under `frontend/ui/src` (+ `frontend/ui/src/mocks` read-only test doubles and `tests/e2e`), consumes the shipped P9 contract exactly, and changes no server, migration, schema, or API code — no new endpoints, no version bump, no tags (merging to main is the release).
