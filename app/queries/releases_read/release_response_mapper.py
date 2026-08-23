"""Maps a ``releases`` table row plus its manifest onto the response model."""

from datetime import datetime

from app.models.responses.release_component_response_model import (
    ReleaseComponentResponseModel,
)
from app.models.responses.release_response_model import ReleaseResponseModel


class ReleaseResponseMapper:
    """Builds :class:`ReleaseResponseModel` values from database rows.

    Centralises the column ordering
    (``id, product_id, product_version, label, notes, created_at``) shared by
    the ledger and single-release read queries so the ``created_at`` timestamp
    is rendered to an ISO-8601 string in exactly one place. The already-assembled
    frozen manifest is attached by the caller.
    """

    @staticmethod
    def to_model(
        row: tuple[object, ...], components: list[ReleaseComponentResponseModel]
    ) -> ReleaseResponseModel:
        """Convert a selected release row and its manifest to a response model.

        Args:
            row: A row of
                ``(id, product_id, product_version, label, notes, created_at)``
                as returned by a ``SELECT`` against the ``releases`` table.
                ``created_at`` is a :class:`datetime.datetime`; ``label`` and
                ``notes`` may be ``None``.
            components: The release's frozen manifest entries.

        Returns:
            The populated :class:`ReleaseResponseModel`.
        """
        (
            release_id,
            product_id,
            product_version,
            label,
            notes,
            created_at,
            bump_level,
            bump_rationale,
        ) = row
        rendered_created_at = (
            created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
        )
        return ReleaseResponseModel(
            id=str(release_id),
            product_id=str(product_id),
            product_version=str(product_version),
            label=None if label is None else str(label),
            notes=None if notes is None else str(notes),
            created_at=rendered_created_at,
            bump_level=None if bump_level is None else str(bump_level),
            bump_rationale=None if bump_rationale is None else str(bump_rationale),
            components=components,
        )
