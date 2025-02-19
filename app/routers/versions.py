from fastapi import APIRouter

from app.models.requests.application_and_version_model import (
    ApplicationAndVersionNameModel,
)
from app.models.requests.application_name_model import ApplicationNameModel
from app.queries.versions.create_version import CreateVersion
from app.queries.versions.delete_version import DeleteVersion
from app.queries.versions.retrieve_latest_version import RetrieveLatestVersion
from app.queries.versions.retrieve_version_history import RetrieveVersionHistory

router = APIRouter(tags=["versions"], prefix="/versions")


@router.get("/")
async def get(data: ApplicationNameModel):
    result = await RetrieveVersionHistory().execute(data=data)

    return {"result": result}


@router.get("/latest")
async def get_all(data: ApplicationNameModel):
    result = await RetrieveLatestVersion().execute(data=data)

    return {"result": result}


@router.post("/")
async def create(data: ApplicationAndVersionNameModel):
    result = await CreateVersion().execute(data=data)

    return {"result": result}


@router.delete("/")
async def read_all(data: ApplicationAndVersionNameModel):
    result = await DeleteVersion().execute(data=data)

    return {"result": result}
