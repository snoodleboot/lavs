from fastapi import APIRouter

from app.models.patch.write_patch_model import WritePatchModel
from app.queries.patch_version.read import get_next_patch_version
from app.queries.rollback_to_previous_patch_version import (
    rollback_to_previous_patch_version,
)

router = APIRouter(tags=["patch"], prefix="/patch")


@router.post("/")
async def create(data: WritePatchModel):
    """Create the next patch version."""
    result = await create(product_name=data.application_name)

    return {"result": result}


@router.get("/")
async def get(application_name):
    """Retrieve the next patch version."""
    result = await get_next_patch_version(product_name=application_name)

    return {"result": result}


@router.post("/rollback")
async def rollback(data: WritePatchModel):
    result = await rollback_to_previous_patch_version(
        product_name=data.application_name
    )

    return {"result": result}
