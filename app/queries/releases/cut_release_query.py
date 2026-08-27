"""Query that cuts an immutable release by freezing the product's manifest."""

import json
from typing import Any

from app.domain.bump_propagation import derive_product_bump, effective_levels
from app.domain.change_classifier import classify_change
from app.domain.product_version import apply_bump
from app.errors.conflict_error import ConflictError
from app.errors.not_found_error import NotFoundError
from app.models.enums.bump_level import BumpLevel
from app.models.enums.bump_policy import BumpPolicy
from app.models.enums.version_status import VersionStatus
from app.models.responses.release_response_model import ReleaseResponseModel
from app.models.types.ulid_id import new_ulid
from app.queries.query import Query
from app.queries.releases.cut_release_request import CutReleaseRequest
from app.queries.releases.cut_release_result import CutReleaseResult
from app.queries.releases.release_manifest_mapper import (
    to_release_components,
    to_release_response,
)

_SELECT_PRODUCT = "SELECT id, base_version, bump_policy FROM products WHERE id = ?"
_SELECT_RELEASE_BY_IDEMPOTENCY = (
    "SELECT id FROM releases WHERE product_id = ? AND idempotency_key = ? LIMIT 1"
)
_SELECT_ACTIVE_COMPONENTS = (
    "SELECT c.id AS component_id, c.name AS name, v.id AS version_id, "
    "v.major AS major, v.minor AS minor, v.patch AS patch, v.prerelease AS prerelease "
    "FROM components c "
    "JOIN versions v ON v.component_id = c.id AND v.status = ? "
    "WHERE c.product_id = ? "
    "ORDER BY c.id"
)
_SELECT_LATEST_RELEASE = (
    "SELECT id, product_version FROM releases WHERE product_id = ? "
    "ORDER BY created_at DESC, id DESC LIMIT 1"
)
_SELECT_PRIOR_MANIFEST = (
    "SELECT rc.component_id, v.major, v.minor, v.patch, v.prerelease "
    "FROM release_components rc "
    "JOIN versions v ON v.id = rc.version_id "
    "WHERE rc.release_id = ?"
)
_SELECT_EDGES = (
    "SELECT from_component_id, to_component_id FROM component_dependencies WHERE product_id = ?"
)
_INSERT_RELEASE = (
    "INSERT INTO releases "
    "(id, product_id, product_version, label, notes, idempotency_key, bump_level, bump_rationale) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)
_INSERT_RELEASE_COMPONENT = (
    "INSERT INTO release_components (release_id, component_id, version_id, change_level) "
    "VALUES (?, ?, ?, ?)"
)
_SELECT_RELEASE = (
    "SELECT id, product_id, product_version, label, notes, created_at, bump_level, bump_rationale "
    "FROM releases WHERE id = ?"
)
_SELECT_RELEASE_MANIFEST = (
    "SELECT rc.component_id AS component_id, c.name AS name, rc.version_id AS version_id, "
    "v.major AS major, v.minor AS minor, v.patch AS patch, v.prerelease AS prerelease, "
    "rc.change_level AS change_level "
    "FROM release_components rc "
    "JOIN components c ON c.id = rc.component_id "
    "JOIN versions v ON v.id = rc.version_id "
    "WHERE rc.release_id = ? "
    "ORDER BY c.id"
)


class CutReleaseQuery(Query[CutReleaseResult]):
    """Freeze a product's current composition into an immutable release.

    A cut snapshots each component's currently-``active`` version, derives the
    server-owned ``product_version``, and persists one ``releases`` row plus a
    ``release_components`` row pinning each version id. The bump is derived per
    the product's ``bump_policy``: ``legacy`` applies an unconditional minor bump
    (byte-identical to the pre-P9 behaviour); ``default`` classifies each
    component's change against the previous release manifest and takes the
    graph-wide maximum (see :mod:`app.domain.bump_propagation`). The derived
    ``bump_level`` and a JSON ``bump_rationale`` are recorded on the release, and
    each component's own ``change_level`` on its manifest row. Because versions
    are immutable and the manifest pins ``version_id``s, a cut release never
    changes afterward. When an ``Idempotency-Key`` repeats a prior cut for the
    product, the existing release is returned unchanged (``created=False``).
    """

    async def apply(self, data: CutReleaseRequest, conn: Any) -> CutReleaseResult:
        """Cut a release (or replay an idempotent one) for the product.

        Args:
            data: The cut request (product id, optional label/notes, optional
                idempotency key).
            conn: Live database connection.

        Returns:
            The frozen release plus whether it was newly created.

        Raises:
            NotFoundError: When ``data.product_id`` does not exist.
            ConflictError: When no component has an ``active`` version to
                release.
        """
        product_rows = conn.execute(_SELECT_PRODUCT, (data.product_id,)).fetchall()
        if len(product_rows) == 0:
            raise NotFoundError(
                message=f"Product '{data.product_id}' does not exist.",
                details={"product_id": data.product_id},
            )
        base_version = product_rows[0][1]
        bump_policy = str(product_rows[0][2])

        if data.idempotency_key is not None:
            existing = conn.execute(
                _SELECT_RELEASE_BY_IDEMPOTENCY, (data.product_id, data.idempotency_key)
            ).fetchall()
            if len(existing) > 0:
                release = self._load_release(conn, existing[0][0])
                return CutReleaseResult(release=release, created=False)

        active = conn.execute(
            _SELECT_ACTIVE_COMPONENTS, (VersionStatus.ACTIVE.value, data.product_id)
        )
        active_columns = [entry[0] for entry in active.description]
        active_rows = active.fetchall()
        if len(active_rows) == 0:
            raise ConflictError(
                message=(
                    f"Product '{data.product_id}' has no components with an active "
                    "version; nothing to release."
                ),
                details={"product_id": data.product_id},
            )
        active_records = [dict(zip(active_columns, row, strict=False)) for row in active_rows]

        latest = conn.execute(_SELECT_LATEST_RELEASE, (data.product_id,)).fetchall()
        latest_release_id = latest[0][0] if len(latest) > 0 else None
        latest_version = latest[0][1] if len(latest) > 0 else None
        current = latest_version if latest_version is not None else base_version

        bump_level, rationale, change_by_component = self._derive(
            conn, data.product_id, bump_policy, active_records, latest_release_id
        )
        product_version = apply_bump(current, bump_level)

        release_id = new_ulid()
        _ = conn.execute(
            _INSERT_RELEASE,
            (
                release_id,
                data.product_id,
                product_version,
                data.label,
                data.notes,
                data.idempotency_key,
                bump_level.value,
                rationale,
            ),
        )
        for record in active_records:
            _ = conn.execute(
                _INSERT_RELEASE_COMPONENT,
                (
                    release_id,
                    record["component_id"],
                    record["version_id"],
                    change_by_component.get(str(record["component_id"])),
                ),
            )

        release = self._load_release(conn, release_id)
        return CutReleaseResult(release=release, created=True)

    def _derive(
        self,
        conn: Any,
        product_id: str,
        bump_policy: str,
        active_records: list[dict[str, Any]],
        latest_release_id: Any,
    ) -> tuple[BumpLevel, str | None, dict[str, str]]:
        """Derive the release bump, rationale, and per-component change levels.

        ``legacy`` (and any non-``default`` policy) forces an unconditional minor
        bump with no rationale or per-component change level — byte-identical to
        the pre-P9 behaviour. ``default`` classifies each active component's
        change against the previous release manifest, walks the dependency graph,
        and takes the graph-wide maximum.

        Args:
            conn: Live database connection.
            product_id: The product being cut.
            bump_policy: The product's stored bump policy.
            active_records: The active-component field dicts for this cut.
            latest_release_id: The id of the product's previous release, or
                ``None`` when it has never been released.

        Returns:
            The derived ``(bump_level, bump_rationale_json_or_None,
            change_level_by_component_id)``.
        """
        if bump_policy != BumpPolicy.DEFAULT.value:
            return BumpLevel.MINOR, None, {}

        prior = self._prior_manifest(conn, latest_release_id)
        own_levels: dict[str, BumpLevel] = {}
        for record in active_records:
            component_id = str(record["component_id"])
            current_tuple = (
                int(record["major"]),
                int(record["minor"]),
                int(record["patch"]),
                record["prerelease"],
            )
            own_levels[component_id] = classify_change(prior.get(component_id), current_tuple)

        active_ids = {str(record["component_id"]) for record in active_records}
        removed_any = any(component_id not in active_ids for component_id in prior)
        edges = [
            (str(row[0]), str(row[1]))
            for row in conn.execute(_SELECT_EDGES, (product_id,)).fetchall()
        ]

        bump_level = derive_product_bump(own_levels, edges, removed_any)
        effective = effective_levels(own_levels, edges)
        rationale = json.dumps(
            {
                "policy": BumpPolicy.DEFAULT.value,
                "product_bump": bump_level.value,
                "removed_any": removed_any,
                "components": {
                    component_id: {
                        "own": own_levels[component_id].value,
                        "effective": effective[component_id].value,
                    }
                    for component_id in own_levels
                },
            },
            sort_keys=True,
        )
        change_by_component = {
            component_id: level.value for component_id, level in own_levels.items()
        }
        return bump_level, rationale, change_by_component

    def _prior_manifest(
        self, conn: Any, latest_release_id: Any
    ) -> dict[str, tuple[int, int, int, str | None]]:
        """Load the previous release's pinned versions, keyed by component id.

        Args:
            conn: Live database connection.
            latest_release_id: The previous release's id, or ``None``.

        Returns:
            ``component_id -> (major, minor, patch, prerelease)`` for the
            previous release; empty when there is none (a first-ever cut).
        """
        if latest_release_id is None:
            return {}
        rows = conn.execute(_SELECT_PRIOR_MANIFEST, (latest_release_id,)).fetchall()
        return {str(row[0]): (int(row[1]), int(row[2]), int(row[3]), row[4]) for row in rows}

    def _load_release(self, conn: Any, release_id: str) -> ReleaseResponseModel:
        """Load a release and its pinned manifest into the response model.

        Args:
            conn: Live database connection.
            release_id: The id of the release to load.

        Returns:
            The release with its frozen component manifest.
        """
        manifest = conn.execute(_SELECT_RELEASE_MANIFEST, (release_id,))
        components = to_release_components(manifest.description, manifest.fetchall())
        release = conn.execute(_SELECT_RELEASE, (release_id,))
        release_rows = release.fetchall()
        return to_release_response(release.description, release_rows[0], components)
