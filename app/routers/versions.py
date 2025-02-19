from typing import Any

from fastapi import APIRouter

from app.models.requests.request_model import RequestModel
from app.queries.versions.create_version import create_version

router = APIRouter(tags=["versions"], prefix="/versions")


@router.get("/")
async def get(data: Any):

    return {"result": ""}


@router.get("/latest")
async def get_all(data: Any):

    return {"result": ""}


@router.post("/")
async def create(data: RequestModel):
    await create_version(
        product_name=data.application_name,
        major=data.major,
        minor=data.minor,
        patch=data.patch,
    )

    return {"result": data}


@router.delete("/")
async def read_all(data: Any):

    return {"result": ""}
