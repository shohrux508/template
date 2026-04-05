# Minimalistic Backend Template

Чистый, асинхронный шаблон backend-приложения на Python 3.12+, объединяющий Telegram-бота (aiogram 3.x), API (FastAPI) и **инженерный слой библиотек-оберток** (`libs/`).

## Особенности

- **Асинхронность**: Полная поддержка `asyncio` (async/await во всех сетевых операциях).
- **Гибкость**: Запуск только бота, только API или обоих сервисов одновременно.
- **Plug-and-Play**: Инициализация любого модуля — одна строка в `app.py`.
- **Strict Typing**: 100% Type Hints, Pydantic-модели для передачи данных между модулями.
- **Self-Contained**: Каждый модуль `libs/` содержит свою логику ошибок, а конфигурацию получает из `app.config`.
- **Конфигурация**: Переменные окружения через `.env` (Pydantic Settings).

## Структура проекта

```
project/
├── app/
│   ├── api/              # FastAPI компоненты
│   ├── telegram/          # Aiogram компоненты
│   ├── services/          # Бизнес-логика
│   ├── app.py             # Orchestrator (сборка и запуск)
│   ├── config.py          # Единые настройки (Pydantic Settings)
│   └── container.py       # DI-контейнер / реестр сервисов
├── libs/                   # ⚡ Инженерный слой
│   ├── ai/                # Интеллект
│   │   ├── engine.py      # LLM (OpenAI / Anthropic)
│   │   └── rag.py         # Векторный поиск (Qdrant)
│   ├── iot/               # Нервная система
│   │   ├── mqtt.py        # MQTT-клиент (aiomqtt)
│   │   └── ws_client.py   # WebSocket-клиент (websockets)
│   ├── data/              # Аналитика
│   │   ├── analysis.py    # Обработка данных (Pandas / Numpy)
│   │   └── viz.py         # Визуализация (Matplotlib / Plotly)
│   ├── crawler/           # Сбор данных
│   │   ├── browser.py     # Playwright-автоматизация
│   │   └── parser.py      # HTML-парсинг (Selectolax / BS4)
│   ├── ui/                # Интерфейс
│   │   └── console.py     # Красивый терминал (Rich)
│   └── utils/             # Системный фундамент
│       ├── http.py        # Async HTTP-клиент (httpx)
│       ├── scheduler.py   # Фоновые задачи (APScheduler)
│       ├── cache.py       # Redis-хранилище
│       └── logger.py      # Конфигурация Loguru
├── tests/                  # Тесты (pytest)
├── main.py                 # Точка входа
├── .env                    # Конфигурация
└── requirements.txt        # Зависимости
```

## Установка и запуск

1. **Клонируйте репозиторий** (или используйте как шаблон).

2. **Установите зависимости**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Настройте окружение** — создайте `.env` в корне проекта:
   ```env
   # ── Запуск компонентов ─────────────────────────────
   BOT_TOKEN=your_telegram_bot_token
   RUN_TELEGRAM=true
   RUN_API=true
   API_HOST=0.0.0.0
   API_PORT=8000

   # ── AI / LLM ──────────────────────────────────────
   LLM_PROVIDER=openai
   LLM_API_KEY=sk-...
   LLM_MODEL=gpt-4o-mini

   # ── MQTT ───────────────────────────────────────────
   MQTT_HOST=localhost
   MQTT_PORT=1883

   # ── Redis ──────────────────────────────────────────
   REDIS_HOST=localhost
   REDIS_PORT=6379

   # ── Логирование ────────────────────────────────────
   LOG_LEVEL=INFO
   ```

4. **Запустите приложение**:
   ```bash
   python main.py
   ```

5. **Запустите тесты**:
   ```bash
   pytest -v
   ```

## Конфигурация (.env)

| Переменная | Описание | По умолчанию |
|---|---|---|
| `BOT_TOKEN` | Токен Telegram бота | `None` |
| `API_HOST` | Хост API сервера | `0.0.0.0` |
| `API_PORT` | Порт API сервера | `8000` |
| `RUN_TELEGRAM` | Запускать бота | `true` |
| `RUN_API` | Запускать API | `true` |
| `LLM_PROVIDER` | Провайдер LLM (`openai` / `anthropic`) | `openai` |
| `LLM_API_KEY` | API-ключ LLM | `""` |
| `LLM_MODEL` | Модель LLM | `gpt-4o-mini` |
| `LLM_BASE_URL` | Base URL для self-hosted / proxy | `None` |
| `QDRANT_URL` | URL Qdrant-сервера | `http://localhost:6333` |
| `QDRANT_API_KEY` | API-ключ Qdrant | `None` |
| `EMBEDDING_API_KEY` | API-ключ для эмбеддингов | `""` |
| `EMBEDDING_MODEL` | Модель эмбеддингов | `text-embedding-3-small` |
| `MQTT_HOST` | Хост MQTT-брокера | `localhost` |
| `MQTT_PORT` | Порт MQTT | `1883` |
| `MQTT_USER` | MQTT логин | `None` |
| `MQTT_PASSWORD` | MQTT пароль | `None` |
| `WS_URL` | URL WebSocket-сервера | `ws://localhost:8080/ws` |
| `REDIS_HOST` | Хост Redis | `localhost` |
| `REDIS_PORT` | Порт Redis | `6379` |
| `REDIS_DB` | Номер БД Redis | `0` |
| `REDIS_PASSWORD` | Пароль Redis | `None` |
| `REDIS_KEY_PREFIX` | Префикс ключей Redis | `""` |
| `HTTP_TIMEOUT` | Таймаут HTTP-запросов (сек) | `30.0` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `LOG_FILE` | Путь к файлу логов | `None` |
| `LOG_JSON` | JSON-формат логов | `false` |

## Инженерный слой — libs/

### Принципы

- **Plug-and-Play** — инициализация одной строкой в `app.py`
- **Strict Typing** — Pydantic-модели для конфигов и данных
- **Async First** — все сетевые операции через `async/await`
- **Self-Contained** — каждый модуль обрабатывает свои ошибки
- **Lazy Init** — тяжелые клиенты создаются при первом вызове

### Быстрый старт — использование из бизнес-логики

```python
# В любом сервисе / хендлере, где есть доступ к container:

# AI — задать вопрос LLM
answer = await container.llm.ask("Столица Франции?")

# IoT — отправить команду на ESP32
await container.mqtt.publish("home/light", "on")

# Data — обработать метрики датчиков
df = container.analysis.process_metrics(raw_data)
plot_path = container.viz.render_plot(df, column="temperature")

# Utils — HTTP-запрос к внешнему API
weather = await container.http.get_json("https://api.weather.com/current")

# Utils — кэш Redis
await container.cache.set_val("sensor:1:temp", "22.5", ttl=300)

# Utils — фоновые задачи
container.scheduler.add_interval(check_sensors, minutes=5)

# Crawler — парсинг HTML
items = container.parser.css_select(html, "div.product",
    fields={"name": "h2", "price": "span.price"})

# UI — красивый вывод в терминал
container.console.table(data, title="Отчет за день")
```

### Описание модулей

#### `libs/ai/engine.py` — LLM Engine
- Поддержка OpenAI и Anthropic через единый интерфейс
- `ask()` — простой запрос → текст
- `ask_stream()` — стриминговый ответ (async generator)
- Ленивое создание клиента (импорт при первом вызове)

#### `libs/ai/rag.py` — RAG Pipeline
- Векторный поиск через Qdrant
- Эмбеддинги через OpenAI
- `index_documents()` / `search()` — полный цикл RAG

#### `libs/iot/mqtt.py` — MQTT Client
- Обертка над `aiomqtt` с автоматическим реконнектом
- `publish()` — отправка команд
- `subscribe()` — async generator входящих сообщений
- `@on_message()` — декоратор-обработчик
- Поддержка wildcard-топиков (`#`, `+`)

#### `libs/iot/ws_client.py` — WebSocket Client
- Чистые WebSockets (без FastAPI-зависимостей)
- Автоматический реконнект при потере связи
- `listen()` — async generator / `connect_and_run()` — callback API

#### `libs/data/analysis.py` — Data Analysis
- `process_metrics()` — сырые данные → DataFrame
- `describe()` — статистическая сводка (Pydantic-модель)
- `filter_outliers()`, `resample_timeseries()`
- Утилиты: `moving_average()`, `normalize()`, `detect_anomalies()`

#### `libs/data/viz.py` — Visualization
- `render_plot()` → `.png` через Matplotlib (для Telegram)
- `render_multi_plot()` — несколько линий
- `render_interactive()` → `.html` через Plotly

#### `libs/crawler/browser.py` — Browser Automation
- Playwright с `async with` context manager
- `get_page_content()`, `screenshot()`, `evaluate()`, `click_and_wait()`
- Настройка proxy, viewport, user-agent

#### `libs/crawler/parser.py` — HTML Parser
- Selectolax (быстрый) с fallback на BeautifulSoup4
- `css_select()` — извлечение по CSS-селекторам
- `extract_table()` — парсинг HTML-таблиц

#### `libs/ui/console.py` — Rich Console
- `info()`, `success()`, `warning()`, `error()` — темизированные сообщения
- `table()`, `tree()`, `json()`, `code()` — форматированный вывод
- `status()` — контекстный менеджер со спиннером

#### `libs/utils/http.py` — HTTP Client
- Единый `httpx.AsyncClient` с ретраями
- `get_json()`, `post_json()`, `download()`
- Настройка base_url, headers, SSL, таймауты

#### `libs/utils/scheduler.py` — Task Scheduler
- APScheduler обертка
- `add_interval()`, `add_cron()`, `add_once()`
- Полный lifecycle: `start()` / `shutdown()`

#### `libs/utils/cache.py` — Redis Cache
- Типизированный API: `get_val()`, `set_val()`, TTL
- Поддержка JSON, Hash, списков, счетчиков
- Авто-префиксация ключей

#### `libs/utils/logger.py` — Loguru Config
- `setup_logger()` — одна функция для настройки всего логирования
- Консоль + файл, ротация, JSON-режим для продакшена

## Использование

### Добавление сервиса
1. Создайте класс в `app/services/`.
2. Зарегистрируйте в `app/app.py` → `setup_services()`:
   ```python
   self.container.register("my_service", MyService())
   ```

### Добавление роутера (Telegram)
1. Создайте роутер в `app/telegram/routers/`.
2. Подключите его в `app/telegram/bot.py`. Роутеры автоматически получат `container` из `Dispatcher`.

### Добавление роутера (API)
1. Создайте роутер в `app/api/routers/`.
2. Подключите его в `app/api/server.py`. Используйте `Depends` из `app/api/dependencies.py`.

### Отключение ненужного модуля libs/
Закомментируйте соответствующую строку `register_lazy(...)` в `app/app.py` → `setup_libs()`.

## Makefile

| Команда | Описание |
|---|---|
| `make run` | Запустить приложение |
| `make test` | Запустить тесты |
| `make test-cov` | Тесты с покрытием |
| `make lint` | Проверка линтером (ruff) |
| `make format` | Форматирование кода |
| `make install` | Установить зависимости |
| `make install-dev` | Зависимости + dev-инструменты |
| `make up` | Поднять инфраструктуру (Docker) |
| `make down` | Остановить инфраструктуру |
| `make clean` | Удалить кэши |

## Docker Compose

Одной командой поднимает всю инфраструктуру для разработки:

```bash
docker compose up -d    # или: make up
```

| Сервис | Порт | Назначение |
|---|---|---|
| **Redis** | 6379 | Кэш, состояние системы |
| **Mosquitto** | 1883 / 9001 | MQTT-брокер (TCP + WebSocket) |
| **Qdrant** | 6333 / 6334 | Векторная БД для RAG (REST + gRPC) |

## Стек технологий

| Категория | Библиотеки |
|---|---|
| **Core** | Python 3.12+, asyncio, FastAPI, aiogram 3.x, Uvicorn |
| **AI** | OpenAI, Anthropic, Qdrant |
| **IoT** | aiomqtt (paho-mqtt), websockets |
| **Data** | Pandas, Numpy, Matplotlib, Plotly |
| **Crawler** | Playwright, Selectolax, BeautifulSoup4 |
| **Utils** | httpx, APScheduler, Redis, Loguru |
| **UI** | Rich |
| **Config** | Pydantic Settings, python-dotenv |
| **Testing** | pytest, pytest-asyncio |
