"""Query that computes which components a hypothetical change would impact."""

from app.connections.db_session import DbSession
from app.domain.bump_propagation import effective_levels
from app.errors.not_found_error import NotFoundError
from app.models.enums.bump_level import BumpLevel
from app.models.responses.impact_response_model import ImpactResponseModel
from app.models.responses.impacted_component_model import ImpactedComponentModel
from app.queries.component_dependencies.impact_request import ImpactRequest
from app.queries.query import Query

_SELECT_PRODUCT = "SELECT id FROM products WHERE id = ?"
_SELECT_COMPONENT = "SELECT id FROM components WHERE id = ? AND product_id = ?"
_SELECT_COMPONENTS = "SELECT id FROM components WHERE product_id = ? ORDER BY id"
_SELECT_EDGES = (
    "SELECT from_component_id, to_component_id FROM component_dependencies WHERE product_id = ?"
)


class ImpactQuery(Query[ImpactResponseModel]):
    """Project a hypothetical **major** change to one component across its dependents.

    Every other component starts at ``NONE``; the target is set to ``MAJOR`` and
    the propagation walk yields each transitive dependent's projected change
    level. Only components actually affected (projected level above ``NONE``) are
    returned. Read-only.
    """

    async def apply(self, data: ImpactRequest, conn: DbSession) -> ImpactResponseModel:
        """Compute the impacted dependents for a hypothetical major change.

        Args:
            data: The product id and the component to hypothetically change.
            conn: The live database connection.

        Returns:
            The impacted dependents with their projected change levels.

        Raises:
            NotFoundError: When the product or the component does not exist (the
                component must belong to the product).
        """
        if conn.execute(_SELECT_PRODUCT, [data.product_id]).fetchone() is None:
            raise NotFoundError(
                message=f"Product '{data.product_id}' does not exist.",
                details={"product_id": data.product_id},
            )
        if conn.execute(_SELECT_COMPONENT, [data.component_id, data.product_id]).fetchone() is None:
            raise NotFoundError(
                message=(
                    f"Component '{data.component_id}' does not exist in product "
                    f"'{data.product_id}'."
                ),
                details={"component_id": data.component_id, "product_id": data.product_id},
            )

        component_ids = [
            str(row[0]) for row in conn.execute(_SELECT_COMPONENTS, [data.product_id]).fetchall()
        ]
        own_levels = dict.fromkeys(component_ids, BumpLevel.NONE)
        own_levels[data.component_id] = BumpLevel.MAJOR

        edges = [
            (str(row[0]), str(row[1]))
            for row in conn.execute(_SELECT_EDGES, [data.product_id]).fetchall()
        ]
        effective = effective_levels(own_levels, edges)

        impacted = [
            ImpactedComponentModel(
                component_id=component_id,
                projected_change_level=effective[component_id].value,
            )
            for component_id in component_ids
            if component_id != data.component_id and effective[component_id] is not BumpLevel.NONE
        ]
        return ImpactResponseModel(component_id=data.component_id, impacted=impacted)
