"""
libs.utils.logger — Конфигурация Loguru.

Пример использования (в main.py):
    from libs.utils.logger import setup_logger
    setup_logger(level="DEBUG", json_output=False)
"""

from __future__ import annotations

import sys

from loguru import logger


def setup_logger(
    *,
    level: str = "INFO",
    fmt: str | None = None,
    json_output: bool = False,
    log_file: str | None = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
    colorize: bool = True,
) -> None:
    """Настроить Loguru-логгер для всего приложения.

    Args:
        level: Минимальный уровень логирования (DEBUG, INFO, WARNING, ERROR).
        fmt: Формат строки (если None — используется стандартный с цветами).
        json_output: Если True — вывод в JSON-формате (для продакшена / ELK).
        log_file: Путь к файлу логов (опционально).
        rotation: Ротация файла логов.
        retention: Хранение старых файлов логов.
        colorize: Цветной вывод в консоль.
    """
    # Удаляем дефолтный хендлер
    logger.remove()

    # Формат по умолчанию
    default_fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    )

    final_fmt = fmt or default_fmt

    # Консольный хендлер
    if json_output:
        logger.add(
            sys.stderr,
            level=level,
            serialize=True,
            colorize=False,
        )
    else:
        logger.add(
            sys.stderr,
            level=level,
            format=final_fmt,
            colorize=colorize,
        )

    # Файловый хендлер (опционально)
    if log_file:
        logger.add(
            log_file,
            level=level,
            format=final_fmt.replace("<green>", "")
            .replace("</green>", "")
            .replace("<level>", "")
            .replace("</level>", "")
            .replace("<cyan>", "")
            .replace("</cyan>", ""),
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
        )
        logger.info("Логирование в файл: {}", log_file)

    logger.info("Loguru настроен (level={})", level)
