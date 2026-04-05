from aiogram import Router, types
from aiogram.filters import CommandStart
from typing import TYPE_CHECKING
from app.container import Container

if TYPE_CHECKING:
    from app.services.example_service import ExampleService

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, container: Container):
    example_service: "ExampleService" = container.get("example_service")
    msg = example_service.get_message()
    await message.answer(f"Bot says: {msg}")
