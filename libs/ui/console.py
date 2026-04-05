"""
libs.ui.console — Красивый вывод в терминал через Rich.

Пример использования:
    console = Console()
    console.info("Сервер запущен", port=8000)
    console.table(data, title="Пользователи")
    with console.status("Загрузка..."):
        await long_operation()
"""

from __future__ import annotations

from typing import Any
from contextlib import contextmanager

from loguru import logger


class Console:
    """Красивый терминальный вывод на базе Rich."""

    def __init__(self, *, width: int | None = None) -> None:
        from rich.console import Console as RichConsole
        from rich.theme import Theme

        custom_theme = Theme({
            "info": "cyan",
            "success": "bold green",
            "warning": "bold yellow",
            "error": "bold red",
            "header": "bold magenta",
        })

        self._console = RichConsole(theme=custom_theme, width=width)
        logger.debug("Console инициализирован")

    # ── Сообщения ────────────────────────────────────────────────────────

    def info(self, message: str, **kwargs: Any) -> None:
        """Информационное сообщение."""
        extra = " ".join(f"[dim]{k}={v}[/dim]" for k, v in kwargs.items())
        self._console.print(f"[info]ℹ {message}[/info] {extra}")

    def success(self, message: str, **kwargs: Any) -> None:
        """Сообщение об успехе."""
        extra = " ".join(f"[dim]{k}={v}[/dim]" for k, v in kwargs.items())
        self._console.print(f"[success]✓ {message}[/success] {extra}")

    def warning(self, message: str, **kwargs: Any) -> None:
        """Предупреждение."""
        extra = " ".join(f"[dim]{k}={v}[/dim]" for k, v in kwargs.items())
        self._console.print(f"[warning]⚠ {message}[/warning] {extra}")

    def error(self, message: str, **kwargs: Any) -> None:
        """Ошибка."""
        extra = " ".join(f"[dim]{k}={v}[/dim]" for k, v in kwargs.items())
        self._console.print(f"[error]✗ {message}[/error] {extra}")

    def header(self, message: str) -> None:
        """Заголовок-разделитель."""
        self._console.rule(f"[header]{message}[/header]")

    # ── Таблицы ──────────────────────────────────────────────────────────

    def table(
        self,
        data: list[dict[str, Any]],
        *,
        title: str = "",
        columns: list[str] | None = None,
    ) -> None:
        """Вывести данные в красивой таблице."""
        from rich.table import Table

        if not data:
            self._console.print("[dim]Нет данных для отображения[/dim]")
            return

        cols = columns or list(data[0].keys())

        table = Table(title=title, show_header=True, header_style="bold cyan")
        for col in cols:
            table.add_column(col)

        for row in data:
            table.add_row(*[str(row.get(c, "")) for c in cols])

        self._console.print(table)

    # ── Прогресс / Статус ────────────────────────────────────────────────

    @contextmanager
    def status(self, message: str = "Загрузка..."):
        """Context manager со спиннером."""
        with self._console.status(f"[info]{message}[/info]"):
            yield

    def progress_bar(self, total: int, *, description: str = ""):
        """Вернуть Rich Progress для использования в цикле."""
        from rich.progress import Progress

        return Progress(console=self._console)

    # ── Деревья ──────────────────────────────────────────────────────────

    def tree(self, data: dict[str, Any], *, title: str = "root") -> None:
        """Вывести словарь как дерево."""
        from rich.tree import Tree

        root = Tree(f"[bold]{title}[/bold]")
        self._build_tree(root, data)
        self._console.print(root)

    def _build_tree(self, parent: Any, data: Any) -> None:
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    branch = parent.add(f"[cyan]{key}[/cyan]")
                    self._build_tree(branch, value)
                else:
                    parent.add(f"[cyan]{key}[/cyan] = {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    branch = parent.add(f"[dim][{i}][/dim]")
                    self._build_tree(branch, item)
                else:
                    parent.add(str(item))

    # ── JSON / Syntax ────────────────────────────────────────────────────

    def json(self, data: Any) -> None:
        """Красивый вывод JSON."""
        import json as json_module

        from rich.syntax import Syntax

        text = json_module.dumps(data, indent=2, ensure_ascii=False, default=str)
        syntax = Syntax(text, "json", theme="monokai")
        self._console.print(syntax)

    def code(self, text: str, *, language: str = "python") -> None:
        """Подсветить код."""
        from rich.syntax import Syntax

        syntax = Syntax(text, language, theme="monokai", line_numbers=True)
        self._console.print(syntax)

    # ── Панели ───────────────────────────────────────────────────────────

    def panel(self, content: str, *, title: str = "", style: str = "cyan") -> None:
        """Обрамленная панель с текстом."""
        from rich.panel import Panel

        self._console.print(Panel(content, title=title, border_style=style))
