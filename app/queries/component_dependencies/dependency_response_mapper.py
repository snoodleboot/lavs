"""Maps a ``component_dependencies`` row onto its response model."""

from datetime import datetime

from app.models.responses.dependency_response_model import DependencyResponseModel


class DependencyResponseMapper:
    """Builds :class:`DependencyResponseModel` values from database rows.

    Centralises the column ordering
    (``id, product_id, from_component_id, to_component_id, created_at``) shared by
    the add and graph queries so ``created_at`` is rendered to an ISO-8601 string
    in exactly one place.
    """

    @staticmethod
    def to_model(row: tuple[object, ...]) -> DependencyResponseModel:
        """Convert a selected edge row to a response model.

        Args:
            row: ``(id, product_id, from_component_id, to_component_id,
                created_at)`` as selected from ``component_dependencies``;
                ``created_at`` is a :class:`datetime.datetime`.

        Returns:
            The populated :class:`DependencyResponseModel`.
        """
        edge_id, product_id, from_component_id, to_component_id, created_at = row
        rendered_created_at = (
            created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
        )
        return DependencyResponseModel(
            id=str(edge_id),
            product_id=str(product_id),
            from_component_id=str(from_component_id),
            to_component_id=str(to_component_id),
            created_at=rendered_created_at,
        )
