from fastapi import APIRouter, Depends
from typing import TYPE_CHECKING
from app.api.dependencies import get_example_service

if TYPE_CHECKING:
    from app.services.example_service import ExampleService

router = APIRouter()

@router.get("/ping")
async def ping(example_service: "ExampleService" = Depends(get_example_service)):
    msg = example_service.get_message()
    return {"message": f"API says: {msg}"}
