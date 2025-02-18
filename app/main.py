import logging

import uvicorn

from fastapi import FastAPI

from app.models.crud.write_model import WriteModel
from app.queries.versions.create_version import create_version
from app.queries.versions.retrieve_latest_version import retrieve_latest_version
from app.queries.versions.retrieve_version_history import retrieve_version_history
from app.routers import patch
from app.routers import basic_crud
from app.routers import versions


app = FastAPI()
logger = logging.getLogger("lavs-api")


@app.get("/")
def root():
    logger.info("Welcome to the lowercase acronym versioning system.")
    return "Welcome to the lowercase acronym versioning system."


@app.get("/versions/read")
async def read_versions(application_name):
    result = await retrieve_version_history(product_name=application_name)

    return {"results": result}


@app.get("/versions/read/latest")
async def read_latest_version(application_name):
    result = await retrieve_latest_version(product_name=application_name)

    return {"results": result}


@app.post("/versions/write")
async def create(data: WriteModel):
    await create_version(
        product_name=data.application_name,
        major=data.major,
        minor=data.minor,
        patch=data.patch,
    )

    return {"result": data}


app.include_router(patch.router)
app.include_router(basic_crud.router)
app.include_router(versions.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="localhost", port=8001)
