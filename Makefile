# ═══════════════════════════════════════════════════════════════════════════
#  Makefile — Minimalistic Backend Template
# ═══════════════════════════════════════════════════════════════════════════

.DEFAULT_GOAL := help

# ── Основные команды ─────────────────────────────────────────────────────

.PHONY: run
run: ## Запустить приложение
	python main.py

.PHONY: test
test: ## Запустить тесты
	python -m pytest tests/ -v

.PHONY: test-cov
test-cov: ## Тесты с покрытием
	python -m pytest tests/ -v --cov=app --cov=libs --cov-report=term-missing

.PHONY: lint
lint: ## Проверить код линтером (ruff)
	python -m ruff check app/ libs/ tests/

.PHONY: lint-fix
lint-fix: ## Автоисправление линтером
	python -m ruff check app/ libs/ tests/ --fix

.PHONY: format
format: ## Форматирование кода (ruff)
	python -m ruff format app/ libs/ tests/

.PHONY: typecheck
typecheck: ## Проверка типов (mypy)
	python -m mypy app/ libs/ --ignore-missing-imports

# ── Установка ────────────────────────────────────────────────────────────

.PHONY: install
install: ## Установить зависимости
	pip install -r requirements.txt

.PHONY: install-dev
install-dev: ## Установить зависимости + dev-инструменты
	pip install -r requirements.txt ruff mypy pytest-cov

.PHONY: install-playwright
install-playwright: ## Установить браузеры для Playwright
	python -m playwright install chromium

# ── Docker ───────────────────────────────────────────────────────────────

.PHONY: up
up: ## Поднять инфраструктуру (Redis, MQTT, Qdrant)
	docker compose up -d

.PHONY: down
down: ## Остановить инфраструктуру
	docker compose down

.PHONY: logs
logs: ## Посмотреть логи инфраструктуры
	docker compose logs -f

.PHONY: status
status: ## Статус контейнеров
	docker compose ps

# ── Утилиты ──────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Удалить кэши и временные файлы
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

.PHONY: help
help: ## Показать справку
	@echo ""
	@echo "  Minimalistic Backend Template"
	@echo "  ─────────────────────────────"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
