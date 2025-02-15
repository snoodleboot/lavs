import logging

import uvicorn

from fastapi import FastAPI

from app.models.write_model import WriteModel
from app.queries.create_version import create_version
from app.queries.retrieve_latest_version import retrieve_latest_version
from app.queries.retrieve_version_history import retrieve_version_history

from app.routers import patch


app = FastAPI()
logger = logging.getLogger("lavs-api")


@app.get("/")
def root():
    logger.info("test")
    return "lavs"


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


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="localhost", port=8001)
