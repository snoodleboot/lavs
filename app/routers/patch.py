from fastapi import APIRouter

from app.models.requests.request_model import RequestModel
from app.queries.patch_version.read_current_patch import read_current_patch
from app.queries.patch_version.rollback_to_previous_patch_version import (
    rollback_to_previous_patch_version,
)

router = APIRouter(tags=["patch"], prefix="/patch")


@router.post("/")
async def create(data: RequestModel):
    """Create the next patch version."""
    result = await create(product_name=data.application_name)

    return {"result": result}


@router.get("/")
async def get(application_name):
    """Retrieve the next patch version."""
    result = await read_current_patch(product_name=application_name)

    return {"result": result}


@router.post("/rollback")
async def rollback(data: RequestModel):
    result = await rollback_to_previous_patch_version(
        product_name=data.application_name
    )

    return {"result": result}
