from fastapi import APIRouter

from app.models.write_patch_model import WritePatchModel
from app.queries.patch_version.create import create_next_patch_version
from app.queries.patch_version.read import get_next_patch_version
from app.queries.rollback_to_previous_patch_version import rollback_to_previous_patch_version

router = APIRouter(tags=['patch'])


@router.post("/create")
async def create_next_patch(data: WritePatchModel):
    result = await create_next_patch_version(product_name=data.application_name)

    return {"result": result}

@router.get("/read")
async def get_next_patch(application_name):
    """Retrieve the next patch_version version."""
    result = await get_next_patch_version(product_name=application_name)

    return {"result": result}

@router.post("/rollback")
async def rollback_patch(data: WritePatchModel):
    result = await rollback_to_previous_patch_version(product_name=data.application_name)

    return {"result": result}