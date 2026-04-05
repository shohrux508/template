from aiogram import Router, types
from aiogram.filters import CommandStart
from app.container import Container

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, container: Container):
    example_service = container.get("example_service")
    msg = example_service.get_message()
    await message.answer(f"Bot says: {msg}")
