from typing import Any

from fastapi import APIRouter

from app.models.requests.application_name_model import ApplicationNameModel
from app.queries.crud.retrieve_all import RetrieveAll

router = APIRouter(tags=["crud"], prefix="/crud")



@router.get("/read_all")
async def read_all(data: ApplicationNameModel):
    results = await RetrieveAll().execute(data=data)
    return {"result": results}
