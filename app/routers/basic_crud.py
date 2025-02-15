from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["crud"], prefix="/crud")


@router.post("/")
async def create(data: Any):

    return {"result": ''}

@router.get("/")
async def get(data: Any):

    return {"result": ''}

@router.delete("/")
async def delete(data: Any):

    return {"result": ''}

@router.get("/read_all")
async def read_all(data: Any):

    return {"result": ''}
