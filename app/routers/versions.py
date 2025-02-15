from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["versions"], prefix="/versions")


@router.get("/")
async def get(data: Any):

    return {"result": ""}


@router.get("/latest")
async def get_all(data: Any):

    return {"result": ""}


@router.post("/")
async def create(data: Any):

    return {"result": ""}


@router.delete("/")
async def read_all(data: Any):

    return {"result": ""}
