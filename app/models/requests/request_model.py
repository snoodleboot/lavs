from pydantic import BaseModel


class RequestModel(BaseModel):
    product_name: str
