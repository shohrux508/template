"""
libs.crawler.parser — HTML-парсинг (Selectolax / BeautifulSoup4).

Пример использования:
    parser = ParserService()
    items = parser.css_select(html, "div.product", fields={"name": "h2", "price": "span.price"})
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from loguru import logger


# ── Модели данных ────────────────────────────────────────────────────────────


class ParsedItem(BaseModel):
    """Один извлеченный элемент."""

    fields: dict[str, str] = Field(default_factory=dict)
    raw_html: str = ""


# ── Сервис ───────────────────────────────────────────────────────────────────


class ParserService:
    """HTML-парсер с поддержкой Selectolax (быстро) и BS4 (fallback)."""

    def __init__(self, *, use_selectolax: bool = True) -> None:
        self._use_selectolax = use_selectolax
        self._engine: str = "selectolax" if use_selectolax else "bs4"

        # Проверяем доступность selectolax, иначе fallback
        if use_selectolax:
            try:
                import selectolax  # noqa: F401

                self._engine = "selectolax"
            except ImportError:
                self._engine = "bs4"
                logger.warning("selectolax не найден, используем BeautifulSoup4")

        logger.info("ParserService инициализирован (engine={})", self._engine)

    # ── Публичный API ────────────────────────────────────────────────────

    def css_select(
        self,
        html: str,
        container_selector: str,
        *,
        fields: dict[str, str] | None = None,
    ) -> list[ParsedItem]:
        """Извлечь элементы из HTML по CSS-селекторам.

        Args:
            html: Исходный HTML.
            container_selector: Селектор контейнера-элемента (каждый match = 1 item).
            fields: Словарь {имя_поля: css_селектор} для извлечения вложенных данных.
        """
        if self._engine == "selectolax":
            return self._parse_selectolax(html, container_selector, fields)
        return self._parse_bs4(html, container_selector, fields)

    def extract_text(self, html: str, selector: str) -> list[str]:
        """Извлечь текстовое содержимое всех элементов по селектору."""
        if self._engine == "selectolax":
            return self._extract_text_selectolax(html, selector)
        return self._extract_text_bs4(html, selector)

    def extract_links(self, html: str, selector: str = "a[href]") -> list[dict[str, str]]:
        """Извлечь все ссылки (text + href)."""
        if self._engine == "selectolax":
            return self._extract_links_selectolax(html, selector)
        return self._extract_links_bs4(html, selector)

    def extract_table(self, html: str, table_selector: str = "table") -> list[dict[str, str]]:
        """Извлечь данные из HTML-таблицы как список словарей."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one(table_selector)
        if not table:
            return []

        headers: list[str] = []
        header_row = table.select_one("thead tr") or table.select_one("tr")
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.select("th, td")]

        rows_data: list[dict[str, str]] = []
        body_rows = table.select("tbody tr") or table.select("tr")[1:]

        for row in body_rows:
            cells = [td.get_text(strip=True) for td in row.select("td")]
            if headers and len(cells) == len(headers):
                rows_data.append(dict(zip(headers, cells)))
            else:
                rows_data.append({f"col_{i}": c for i, c in enumerate(cells)})

        logger.info("extract_table: {} строк извлечено", len(rows_data))
        return rows_data

    # ── Selectolax ───────────────────────────────────────────────────────

    def _parse_selectolax(
        self,
        html: str,
        container_selector: str,
        fields: dict[str, str] | None,
    ) -> list[ParsedItem]:
        from selectolax.parser import HTMLParser

        tree = HTMLParser(html)
        containers = tree.css(container_selector)
        results: list[ParsedItem] = []

        for node in containers:
            item_fields: dict[str, str] = {}
            if fields:
                for name, sel in fields.items():
                    child = node.css_first(sel)
                    item_fields[name] = child.text(strip=True) if child else ""

            results.append(ParsedItem(
                fields=item_fields,
                raw_html=node.html or "",
            ))

        logger.info("css_select: {} элементов найдено", len(results))
        return results

    def _extract_text_selectolax(self, html: str, selector: str) -> list[str]:
        from selectolax.parser import HTMLParser

        tree = HTMLParser(html)
        return [node.text(strip=True) for node in tree.css(selector)]

    def _extract_links_selectolax(
        self, html: str, selector: str
    ) -> list[dict[str, str]]:
        from selectolax.parser import HTMLParser

        tree = HTMLParser(html)
        links: list[dict[str, str]] = []
        for node in tree.css(selector):
            href = node.attributes.get("href", "")
            text = node.text(strip=True)
            links.append({"href": href or "", "text": text})
        return links

    # ── BeautifulSoup4 ───────────────────────────────────────────────────

    def _parse_bs4(
        self,
        html: str,
        container_selector: str,
        fields: dict[str, str] | None,
    ) -> list[ParsedItem]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        containers = soup.select(container_selector)
        results: list[ParsedItem] = []

        for node in containers:
            item_fields: dict[str, str] = {}
            if fields:
                for name, sel in fields.items():
                    child = node.select_one(sel)
                    item_fields[name] = child.get_text(strip=True) if child else ""

            results.append(ParsedItem(
                fields=item_fields,
                raw_html=str(node),
            ))

        logger.info("css_select: {} элементов найдено", len(results))
        return results

    def _extract_text_bs4(self, html: str, selector: str) -> list[str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        return [el.get_text(strip=True) for el in soup.select(selector)]

    def _extract_links_bs4(self, html: str, selector: str) -> list[dict[str, str]]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        links: list[dict[str, str]] = []
        for el in soup.select(selector):
            href = el.get("href", "")
            text = el.get_text(strip=True)
            links.append({"href": str(href), "text": text})
        return links
