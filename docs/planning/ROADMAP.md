# LAVS Roadmap

Gap-closure roadmap for **LAVS** (lowercase acronym versioning system) — a centralized
REST service that integrates independently-versioned software components into a coherent
*product* version across disparate build pipelines.

See also: [ARCHITECTURE.md](../design/ARCHITECTURE.md) · [UI_CONCEPT.md](../design/UI_CONCEPT.md) · [API_CONTRACT.md](../design/API_CONTRACT.md)

---

## 1. Vision & current state

The problem LAVS solves: when a product is assembled from decoupled components (libraries,
services, UIs, CLIs) each evolving on its own pipeline, there is no sane single owner of
"the product version." Forcing every component to share one version is wrong; having no
integrated version is also wrong. LAVS is the external authority that records per-component
versions and **derives a coherent product version** by pinning a specific component version
into a named release.

Today we are at ~30% of that vision: a clean FastAPI skeleton doing CRUD over a single flat
`Versions` table in DuckDB, with an API-key module that isn't wired in and a container build
that doesn't work. The integrating idea — products composed of components, and releases that
pin component versions — does not exist yet. This roadmap closes that gap in five phases.

**v2 north star — product dependency graphs.** With v1's release/version/manifest spine green,
v2 makes a product's version a *derived* fact of what actually changed inside it. The chosen
sequencing is **internal DAG first**: **P9** lands an intra-product component dependency graph and
a cut-time derivation that classifies each component's real change and takes the graph-wide max
(replacing the blind minor-bump); **P10** lifts the same edge primitive to cross-product
composition. Existing products are unaffected until an operator opts a product onto the graph
policy (per-product `bump_policy`, default `legacy`).

## 2. Guiding principles

- **DuckDB-local / Postgres-prod parity** — identical API and behavior on both; DuckDB is the
  default for local dev, PostgreSQL is the production backend.
- **Immutable version history** — versions are append-only; rollback changes status, never deletes.
- **Parameterized SQL only** — no string-interpolated queries, ever.
- **API-first** — every capability is a documented endpoint before it is a UI feature.
- **Innovative UI** — the frontend is a first-class, non-vanilla experience (see UI concept).
- **Derived, explainable versions** — a release records *why* it got the version it did
  (per-component change + dominating node), not just the number.

## 3. Phases

| Phase | Goal | Key outcomes | Exit criteria |
|-------|------|--------------|---------------|
| **P0 Stabilize** | Make it correct & deployable | Fixed Docker image, version drift, security/correctness bugs, wired auth | Container builds & runs; auth enforced; zero string-SQL; CI green |
| **P1 Domain model** | Products → Components → immutable Versions | New schema + config-driven init; endpoints refactored onto it | Register product→components→versions; history retained |
| **P2 Release integration ⭐** | Derive a coherent product version | `releases` + `release_components`; snapshot & manifest endpoints | Produce & retrieve a product release manifest from mixed component versions |
| **P3 Multi-DB** | Production persistence | Backend interface + dialect DDL; Postgres/MySQL/SQL Server | Same API suite passes on DuckDB **and** PostgreSQL |
| **P4 Auth (OSS)** | Real auth for the OSS v1 | Pluggable providers: password+sessions (signup, email + domain validation) + API key | A user can sign up (verified), log in, and use the UI; headless clients use API keys |
| **P5 Frontend** | The Constellation UI | TS/React app over the API w/ live SSE updates | Browse products/components/versions/releases; cut a release; streams update live |
| **P6 EE (Stytch)** *fast-follow* | Enterprise edition | Stytch provider behind the existing auth abstraction | EE build authenticates via Stytch; OSS untouched |
| **P9 Dependency graphs** *(v2)* | Intra-product DAG + derived versions | `component_dependencies` on all 4 backends; cut-time change derivation replaces the blind minor-bump; per-product `bump_policy` | Non-vacuous 4-backend parity; `default`-policy cut derives major/minor/patch/none, `legacy` byte-identical; `POST/DELETE /dependencies`, `GET /graph`, `GET /impact`; SSE `dependency.added/removed` |

**Realtime (cross-cutting, lands with P2/P5):** an SSE channel (`GET /products/{id}/events`)
pushes `version.created` / `version.rolled_back` / `release.cut` so the UI updates live. See
[API_CONTRACT.md §6](../design/API_CONTRACT.md).

```mermaid
gantt
    title LAVS Roadmap (indicative, ~2-week phases)
    dateFormat YYYY-MM-DD
    axisFormat %b %d
    section P0 Stabilize
    Docker/uv/versions/bugs/auth-wiring   :p0, 2026-06-24, 10d
    section P1 Domain model
    Products/Components/immutable versions :p1, after p0, 14d
    section P2 Release integration
    Releases + product-version derivation  :crit, p2, after p1, 14d
    section P3 Multi-DB
    Backend interface + PG/MySQL/MSSQL     :p3, after p2, 18d
    section P4 Auth (OSS)
    Password+sessions, email/domain, API key :p4, after p2, 14d
    section P5 Frontend
    Constellation UI + live SSE            :p5, after p4, 16d
    section P6 EE (fast-follow)
    Stytch provider                        :p6, after p5, 8d
    section P9 Dependency graphs (v2)
    Intra-product DAG + derived versions   :p9, after p6, 20d
```

## 4. Phase detail

### P0 — Stabilize *(blocking)*

- [ ] **Fix the Dockerfile** — currently uses Poetry and copies a nonexistent `poetry.lock`. Switch to **uv**, base image `python:3.14` (not 3.13), and align the port (main.py runs **8001** but the Docker `CMD`/Helm expect **8080**).
- [ ] **Fix version drift** — set ruff `target-version` and pyright `pythonVersion` to **3.14** (`requires-python` is `>=3.14`).
- [ ] **Fix SQL injection** — [create_patch.py](../../app/queries/patch_version/create_patch.py) builds an `INSERT` with f-string interpolation of `product_name`. Parameterize it.
- [ ] **Anchor the semver regex** — [application_and_version_model.py](../../app/models/requests/application_and_version_model.py) uses an unanchored `[0-9]+\.[0-9]+\.[0-9]+`, so `1.2.3.4` and `1.2.3abc` pass. Use `^...$`.
- [ ] **Non-destructive rollback** — [rollback_to_previous_patch_version.py](../../app/queries/patch_version/rollback_to_previous_patch_version.py) `DELETE`s the current row. Replace with a status flag (`rolled_back`) that preserves history.
- [ ] **Wire auth (seed)** — apply the API-key dependency from [api_key.py](../../app/security/api_key.py) to all routers (built + tested, currently unused). This is the minimal gate; the full pluggable auth layer arrives in P4.
- [ ] **Connection lifecycle** — manage the DB connection via FastAPI `lifespan` + a dependency, not per-query.
- [ ] **Cleanup** — delete the stray root file `6.0.0` (accidental pip-output redirect) and remove dead commented code in [main.py](../../app/main.py).

**Acceptance:** container builds & runs; auth enforced when `LAVS_API_KEY` is set; no string-interpolated SQL anywhere; CI (`.github/workflows/python-test.yml`) green.

### P1 — Domain model

- [ ] Introduce `products`, `components`, and immutable `versions` (status: `active|superseded|rolled_back`).
- [ ] Build **config-driven schema initialization** (the `#TODO` in [database.yaml](../../app/configurations/database.yaml) anticipates this).
- [ ] Refactor `/versions` and `/patch` onto the new model.
- [ ] **Move mutations from query-params to request bodies.**
- [ ] Rollback marks status; never deletes.

**Acceptance:** can register product → components → versions; full history retained and queryable.

### P2 — Release integration ⭐ *(the core value)*

- [ ] Add `releases` + `release_components` (pin one version per component).
- [ ] Endpoint to **snapshot** the current active component versions into a named product release.
- [ ] Endpoint to **derive/retrieve** a product version and its release manifest.

**Acceptance:** given N components at mixed versions, produce and retrieve a single coherent product release manifest.

### P3 — Multi-DB backends

- [ ] Define a backend interface (`connect` / `execute` / `init_schema`) with dialect-aware DDL generation — `register_backend()` in [connection_factory.py](../../app/connections/connection_factory.py) already scaffolds this.
- [ ] Implement **PostgreSQL** first, then **MySQL**, then **SQL Server**.
- [ ] Testcontainers-based integration tests per backend.

**Acceptance:** the identical API test suite passes on **DuckDB and PostgreSQL**.

### P4 — Auth (OSS) *(the v1 auth cut)*

OSS auth per [API_CONTRACT.md §1–2](../design/API_CONTRACT.md). Auth is **pluggable** and
selected by deploy config (`LAVS_AUTH_MODES`). EE/Stytch is **out of scope here** — see P6.

- [ ] **Provider abstraction** — `AuthProvider.authenticate(request) -> Principal | 401`; a FastAPI dependency resolves the principal (supersedes the bare P0 key-wiring). Built to accept a Stytch provider later without touching resource routes.
- [ ] **OSS password + sessions** — signup, password hashing, `HttpOnly` session cookies, login/logout/`/auth/me`.
- [ ] **Email + domain validation** — verification-token email flow; signup restricted to an allowed-domain list.
- [ ] **API-key provider** — wrap the existing module for headless/deploy clients.
- [ ] `/health`/`/meta` reports `edition` + enabled `auth_modes` so the UI picks the right login.

**Acceptance:** a user can sign up (with email + domain verification), log in, and operate the UI; headless clients authenticate via API key.

### P5 — Frontend UI

- [ ] Build the **Constellation** UI (see [UI_CONCEPT.md](../design/UI_CONCEPT.md)) in `frontend/ui` (TypeScript 6 / pnpm / vitest) against [API_CONTRACT.md](../design/API_CONTRACT.md).
- [ ] Initial load via `GET /products/{id}/timeline` + `/releases`; **live updates via SSE**.
- [ ] Login UX adapts to the active edition/auth mode.

**Acceptance:** browse products/components/versions/releases, cut a release from the UI, and see streams update live as versions/releases happen.

### P6 — EE (Stytch) *(fast-follow, after OSS v1)*

- [ ] Implement `StytchProvider` behind the existing `AuthProvider` abstraction; verify Stytch sessions, issue a LAVS session.
- [ ] UI renders the Stytch widget when `edition=ee` / `stytch` is in `LAVS_AUTH_MODES`.

**Acceptance:** an EE build authenticates via Stytch; the OSS build and all resource routes are unchanged.

### P9 — Dependency Graphs *(v2, intra-product DAG + change propagation)*

Replaces `product_version.next_product_version`'s blind minor-bump with a cut-time,
per-component-diff bump derived over an intra-product component DAG. A per-product `bump_policy`
column pins existing products to a `legacy` preset (byte-identical to today) while new products
adopt the `default` graph policy. In P9 the DAG edges refine per-component `change_level`,
`bump_rationale`, and the `/impact` what-if — the fixed contraction policy means the product bump
equals the max own-change; propagation moves the version only in P10.

- [ ] `component_dependencies` edge table (product-scoped unique key, ULID id) across
      DuckDB/PG/MySQL/MSSQL + `database.yaml`; non-vacuous 4-backend parity (raw-insert duplicate
      + two-product-scope discriminators).
- [ ] Python-side cycle/self/cross-product/dup rejection (no recursive CTE); dependency CRUD +
      `GET /graph` on the products router.
- [ ] Pure `change_classifier` + `bump_propagation` (topo-sort in Python); `BumpLevel` enum;
      `bump_major`/`bump_patch`/`apply_bump` in `product_version`.
- [ ] Per-product `bump_policy` (`legacy`/`default`, DEFAULT `legacy`); `bump_level`/
      `bump_rationale`/`change_level` columns, threaded through the cut mapper and both read paths
      (nullable, so pre-P9 rows read back).
- [ ] `GET /impact` what-if; SSE `dependency.added`/`removed` + `bump_level` on `release.cut`.
- [ ] *(follow-up)* Constellation edge layer + impact highlight in the frontend.

**Acceptance:** existing empty-edge products on `legacy` produce today's minor bump (no behaviour
change); new `default` products derive major/minor/patch/none and `product_version` is invariant
to intra-product edge presence; each release records `bump_level` + rationale + per-component
`change_level`, surfaced on cut and both read endpoints; cycle/self/cross/dup raise 409, unknown
product/component 404; 4-backend parity not skipped; no tags, no version bump, pyproject stays
`1.0.0`. *(Full plan: [P9_MULTIAGENT_EXECUTION_PLAN.md](P9_MULTIAGENT_EXECUTION_PLAN.md).)*

### P10 — Cross-product composition *(outline)*

Lifts the same `component_dependencies` edge primitive to cross-product: a component may be backed
by another product's release. Because a backing product's `bump_level` is not an active node in
the dependent's own-set, propagation finally moves the dependent product's version (the P9
classifier/propagation modules lift unchanged, being pure and level-based).

- [ ] Edge extension for a `to` of *(product_id, release/version)* — sibling backing table or
      nullable `to_product_id`/`to_release_id` (decided in P10).
- [ ] Reuse the P9 derivation with a backing product's last-cut `bump_level` as the dependency's
      effective level.
- [ ] Cross-product DAG cycle rejection (Python reachability, no recursive CTE).
- [ ] Cross-product edges in `GET /graph`/`impact`, an SSE variant, Constellation rendering.

**Acceptance:** an all-intra-product graph derives identically to P9; mutual product backing is
rejected; no recursive CTEs.

## 5. Cross-cutting

Delivered as **P7 — Release readiness** (the v1 exit checklist, packaged as a phase).

- [x] `/health` and `/ready` endpoints — shipped (P3/P4); pointing the `helm/lavs` probes at them is in flight (P7).
- [ ] OpenAPI docs including the auth scheme (`X-API-Key` header + `lavs_session` cookie) — in flight (P7).
- [ ] Coverage targets — line 80 / branch 70 / function 90. FE thresholds are enforced in `frontend/ui/vite.config.ts` (L80/B70/F90/S85); BE enforcement (L80/B70 via pytest-cov in `pyproject.toml`; function coverage measured/reported only) is in flight (P7). *(Corrected per G-P7b: earlier revisions cited `.prompticorn.yaml`, which does not exist — the thresholds live in the two files above.)*
- [ ] A security review pass (`/security-review`) before any release — the pre-release audit is in flight (P7).

## 6. Open decisions / risks

- **DuckDB concurrency** — single-writer; not suitable for multi-replica prod (hence Postgres). ✅ *Validated (2026-08):* under 64-way concurrent load the **async** resource API is safe (event-loop-serialized on the one shared connection — 200 concurrent writes, 0 errors, no corruption). The single shared `DuckDBPyConnection` is **not** thread-safe, so any **sync** handler touching it from the threadpool races the cursor (`InvalidInputException`); the `/ready` probe hit this (~2% spurious 503 at 64-way) and was fixed by making it `async`. Takeaway: keep all DB access on the event loop (async handlers); DuckDB stays single-process/dev-oriented, Postgres for concurrent/multi-replica prod.
- **Migration** — moving off the flat `Versions` table is a breaking change (accepted). ✅ *Decided & shipped:* a **one-shot data migration**, not start-fresh. `FlatToRelationalMigration` runs on every boot straight after `init_schema`, and is *inspect-then-migrate*: it acts only when a legacy-shaped table (one carrying `product_name`) holds rows **and** `products` is still empty, so a fresh database on any backend is untouched. It creates one product per distinct `product_name`, one synthetic `default` service component per product, and one version per legacy row with `status` preserved 1:1; the legacy table is **archived** (renamed to `legacy_versions`), never dropped, so the original rows — including duplicate semver — survive. ✅ *Backend parity (2026-08):* the migration is exercised against real PostgreSQL, MySQL and SQL Server containers (`tests/backends/test_migration_parity.py`), which closed two dialect bugs it had carried since P3 — the archive step emitted `ALTER TABLE … RENAME TO` (not valid T-SQL; now delegated to `Backend.rename_table`, which SQL Server overrides with `sp_rename`), and the post-archive schema rebuild ran DuckDB's DDL on every backend (now the running backend's own `init_schema`).
