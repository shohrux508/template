import typing
from fastapi import Request

if typing.TYPE_CHECKING:
    from app.services.example_service import ExampleService

def get_example_service(request: Request) -> "ExampleService":
    return request.app.state.container.get("example_service")
