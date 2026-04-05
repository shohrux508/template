"""
Тесты для libs/ — инженерный слой.
"""
import pytest

# ═══════════════════════════════════════════════════════════════════════════
#  Container (+ lazy init)
# ═══════════════════════════════════════════════════════════════════════════

from app.container import Container


class TestContainer:
    def test_register_and_get(self):
        c = Container()
        c.register("svc", {"key": "value"})
        assert c.get("svc") == {"key": "value"}

    def test_register_duplicate_raises(self):
        c = Container()
        c.register("svc", 1)
        with pytest.raises(ValueError, match="уже зарегистрирован"):
            c.register("svc", 2)

    def test_get_missing_raises(self):
        c = Container()
        with pytest.raises(ValueError, match="не найден"):
            c.get("missing")

    def test_has(self):
        c = Container()
        assert c.has("x") is False
        c.register("x", 42)
        assert c.has("x") is True

    def test_register_lazy(self):
        """Фабрика вызывается только при первом get()."""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"lazy": True}

        c = Container()
        c.register_lazy("heavy", factory)

        # Фабрика ещё не вызвана
        assert call_count == 0
        assert c.has("heavy") is True
        assert c.is_initialized("heavy") is False

        # Первый get — вызывает фабрику
        result = c.get("heavy")
        assert result == {"lazy": True}
        assert call_count == 1
        assert c.is_initialized("heavy") is True

        # Второй get — из кэша, фабрика НЕ вызывается повторно
        result2 = c.get("heavy")
        assert result2 == {"lazy": True}
        assert call_count == 1

    def test_register_lazy_duplicate_raises(self):
        c = Container()
        c.register_lazy("x", lambda: 1)
        with pytest.raises(ValueError, match="уже зарегистрирован"):
            c.register_lazy("x", lambda: 2)

    def test_register_lazy_vs_eager_conflict(self):
        c = Container()
        c.register("eager", 1)
        with pytest.raises(ValueError, match="уже зарегистрирован"):
            c.register_lazy("eager", lambda: 2)


# ═══════════════════════════════════════════════════════════════════════════
#  AI — LLMConfig, LLMEngine
# ═══════════════════════════════════════════════════════════════════════════

from libs.ai.engine import LLMConfig, LLMProvider, LLMEngine


class TestLLMConfig:
    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.provider == LLMProvider.OPENAI
        assert cfg.model == "gpt-4o-mini"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 4096

    def test_custom_values(self):
        cfg = LLMConfig(provider="anthropic", api_key="key", model="claude-3-opus")
        assert cfg.provider == LLMProvider.ANTHROPIC
        assert cfg.api_key == "key"

    def test_temperature_bounds(self):
        with pytest.raises(Exception):
            LLMConfig(temperature=3.0)

    def test_engine_init(self):
        engine = LLMEngine(LLMConfig(api_key="test"))
        assert engine.config.api_key == "test"
        assert engine._client is None  # ленивая инициализация


# ═══════════════════════════════════════════════════════════════════════════
#  AI — RAGConfig
# ═══════════════════════════════════════════════════════════════════════════

from libs.ai.rag import RAGConfig, RAGService, Document, SearchResult


class TestRAGConfig:
    def test_defaults(self):
        cfg = RAGConfig()
        assert cfg.qdrant_url == "http://localhost:6333"
        assert cfg.top_k == 5

    def test_document_model(self):
        doc = Document(id="1", text="Hello", metadata={"source": "test"})
        assert doc.id == "1"
        assert doc.metadata["source"] == "test"

    def test_search_result_model(self):
        r = SearchResult(id="1", text="found", score=0.95)
        assert r.score == 0.95

    def test_rag_service_init(self):
        svc = RAGService(RAGConfig())
        assert svc._qdrant is None


# ═══════════════════════════════════════════════════════════════════════════
#  IoT — MQTTConfig
# ═══════════════════════════════════════════════════════════════════════════

from libs.iot.mqtt import MQTTConfig, MQTTService, MQTTMessage


class TestMQTTConfig:
    def test_defaults(self):
        cfg = MQTTConfig()
        assert cfg.host == "localhost"
        assert cfg.port == 1883

    def test_custom(self):
        cfg = MQTTConfig(host="192.168.1.1", port=8883, username="admin")
        assert cfg.username == "admin"

    def test_message_model(self):
        msg = MQTTMessage(topic="sensors/temp", payload="22.5")
        assert msg.topic == "sensors/temp"

    def test_topic_matching(self):
        assert MQTTService._topic_matches("sensors/#", "sensors/temp") is True
        assert MQTTService._topic_matches("sensors/+/data", "sensors/1/data") is True
        assert MQTTService._topic_matches("sensors/temp", "sensors/hum") is False
        assert MQTTService._topic_matches("a/b/c", "a/b") is False


# ═══════════════════════════════════════════════════════════════════════════
#  IoT — WSConfig
# ═══════════════════════════════════════════════════════════════════════════

from libs.iot.ws_client import WSConfig, WSClient


class TestWSConfigAndClient:
    def test_defaults(self):
        cfg = WSConfig()
        assert cfg.url == "ws://localhost:8080/ws"
        assert cfg.reconnect_interval == 3.0

    def test_client_init(self):
        client = WSClient(WSConfig())
        assert client._ws is None
        assert client._running is False


# ═══════════════════════════════════════════════════════════════════════════
#  Data — AnalysisService (Pydantic results)
# ═══════════════════════════════════════════════════════════════════════════

from libs.data.analysis import (
    AnalysisService, AnalysisResult, MetricsSummary,
    AnomalyReport, OutlierReport, ColumnStats, TimeSeriesConfig,
)


class TestAnalysisService:
    def setup_method(self):
        self.svc = AnalysisService()

    def test_process_metrics_empty(self):
        result = self.svc.process_metrics([])
        assert isinstance(result, AnalysisResult)
        assert result.summary.count == 0
        assert result.records == []

    def test_process_metrics_returns_pydantic(self):
        data = [{"temp": 22.0, "hum": 60}, {"temp": 23.5, "hum": 55}]
        result = self.svc.process_metrics(data)
        assert isinstance(result, AnalysisResult)
        assert result.summary.count == 2
        assert "temp" in result.summary.columns
        assert len(result.records) == 2

    def test_process_metrics_df_property(self):
        """AnalysisResult.df возвращает DataFrame для VizService."""
        data = [{"val": 1}, {"val": 2}]
        result = self.svc.process_metrics(data)
        df = result.df
        assert len(df) == 2
        assert "val" in df.columns

    def test_process_metrics_json_serializable(self):
        """AnalysisResult можно сериализовать в JSON (для API / Telegram)."""
        data = [{"temp": 22.5, "hum": 60}]
        result = self.svc.process_metrics(data)
        json_data = result.model_dump()
        assert json_data["summary"]["count"] == 1
        assert isinstance(json_data["summary"]["stats"]["temp"], dict)

    def test_column_stats(self):
        data = [{"val": i} for i in range(10)]
        result = self.svc.process_metrics(data)
        stats = result.summary.stats["val"]
        assert isinstance(stats, ColumnStats)
        assert stats.mean == pytest.approx(4.5)
        assert stats.min == 0.0
        assert stats.max == 9.0

    def test_describe(self):
        import pandas as pd
        df = pd.DataFrame([{"val": i} for i in range(10)])
        summary = self.svc.describe(df)
        assert isinstance(summary, MetricsSummary)
        assert summary.count == 10
        assert "val" in summary.stats

    def test_moving_average(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        result = AnalysisService.moving_average(values, window=3)
        assert len(result) == 5  # len - window + 1
        assert result[0] == pytest.approx(2.0)

    def test_normalize(self):
        values = [0.0, 5.0, 10.0]
        result = AnalysisService.normalize(values)
        assert result == [0.0, 0.5, 1.0]

    def test_detect_anomalies_returns_pydantic(self):
        """detect_anomalies возвращает AnomalyReport (Pydantic)."""
        values = [10.0, 10.1, 9.9, 10.0, 10.2, 9.8, 10.0, 10.1, 9.9, 100.0]
        report = AnalysisService.detect_anomalies(values, threshold=2.0)
        assert isinstance(report, AnomalyReport)
        assert 9 in report.anomaly_indices
        assert report.anomaly_count >= 1
        assert report.total_values == 10

    def test_detect_anomalies_no_anomalies(self):
        values = [10.0, 10.1, 9.9, 10.0]
        report = AnalysisService.detect_anomalies(values, threshold=3.0)
        assert report.anomaly_count == 0
        assert report.anomaly_indices == []

    def test_filter_outliers_returns_pydantic(self):
        """filter_outliers возвращает OutlierReport (Pydantic)."""
        import pandas as pd
        df = pd.DataFrame({"val": [10, 10, 10, 10, 100]})
        report = self.svc.filter_outliers(df, "val", std_factor=1.5)
        assert isinstance(report, OutlierReport)
        assert report.original_count == 5
        assert report.removed_count > 0
        assert report.column == "val"

    def test_filter_outliers_df(self):
        """filter_outliers_df возвращает очищенный DataFrame."""
        import pandas as pd
        df = pd.DataFrame({"val": [10, 10, 10, 10, 100]})
        filtered = self.svc.filter_outliers_df(df, "val", std_factor=1.5)
        assert len(filtered) < len(df)


# ═══════════════════════════════════════════════════════════════════════════
#  Data — VizService
# ═══════════════════════════════════════════════════════════════════════════

from libs.data.viz import VizService, PlotConfig


class TestVizService:
    def test_default_config(self):
        cfg = PlotConfig()
        assert cfg.dpi == 150
        assert cfg.figsize == (12, 6)

    def test_init(self):
        svc = VizService()
        assert svc.default_config is not None


# ═══════════════════════════════════════════════════════════════════════════
#  Crawler — ParserService
# ═══════════════════════════════════════════════════════════════════════════

from libs.crawler.parser import ParserService, ParsedItem


class TestParserService:
    def setup_method(self):
        self.parser = ParserService(use_selectolax=False)

    def test_css_select(self):
        html = '<div class="item"><h2>Title</h2><span>Price</span></div>'
        items = self.parser.css_select(
            html,
            "div.item",
            fields={"name": "h2", "price": "span"},
        )
        assert len(items) == 1
        assert items[0].fields["name"] == "Title"
        assert items[0].fields["price"] == "Price"

    def test_extract_text(self):
        html = "<ul><li>A</li><li>B</li></ul>"
        texts = self.parser.extract_text(html, "li")
        assert texts == ["A", "B"]

    def test_extract_links(self):
        html = '<a href="/page1">Link 1</a><a href="/page2">Link 2</a>'
        links = self.parser.extract_links(html)
        assert len(links) == 2
        assert links[0]["href"] == "/page1"

    def test_extract_table(self):
        html = """
        <table>
            <thead><tr><th>Name</th><th>Value</th></tr></thead>
            <tbody>
                <tr><td>A</td><td>1</td></tr>
                <tr><td>B</td><td>2</td></tr>
            </tbody>
        </table>
        """
        rows = self.parser.extract_table(html)
        assert len(rows) == 2
        assert rows[0]["Name"] == "A"


# ═══════════════════════════════════════════════════════════════════════════
#  Utils — CacheConfig
# ═══════════════════════════════════════════════════════════════════════════

from libs.utils.cache import CacheConfig, CacheService


class TestCacheConfig:
    def test_defaults(self):
        cfg = CacheConfig()
        assert cfg.host == "localhost"
        assert cfg.port == 6379

    def test_key_prefix(self):
        svc = CacheService(CacheConfig(key_prefix="app"))
        assert svc._key("user:1") == "app:user:1"

    def test_no_prefix(self):
        svc = CacheService(CacheConfig())
        assert svc._key("user:1") == "user:1"


# ═══════════════════════════════════════════════════════════════════════════
#  Utils — HttpConfig
# ═══════════════════════════════════════════════════════════════════════════

from libs.utils.http import HttpConfig, HttpClient


class TestHttpConfig:
    def test_defaults(self):
        cfg = HttpConfig()
        assert cfg.timeout == 30.0
        assert cfg.max_retries == 3

    def test_client_init(self):
        client = HttpClient(HttpConfig(base_url="https://api.example.com"))
        assert client.config.base_url == "https://api.example.com"
        assert client._client is None


# ═══════════════════════════════════════════════════════════════════════════
#  Utils — SchedulerService
# ═══════════════════════════════════════════════════════════════════════════

from libs.utils.scheduler import SchedulerService


class TestSchedulerService:
    def test_init(self):
        svc = SchedulerService()
        assert svc._scheduler is None


# ═══════════════════════════════════════════════════════════════════════════
#  UI — Console
# ═══════════════════════════════════════════════════════════════════════════

from libs.ui.console import Console


class TestConsole:
    def test_init(self):
        console = Console()
        assert console._console is not None

    def test_info_no_crash(self):
        console = Console()
        console.info("test message", key="value")

    def test_table_empty(self):
        console = Console()
        console.table([])  # не должен упасть


# ═══════════════════════════════════════════════════════════════════════════
#  ExampleService (обратная совместимость)
# ═══════════════════════════════════════════════════════════════════════════

from app.services.example_service import ExampleService


class TestExampleService:
    def test_get_message(self):
        service = ExampleService()
        assert service.get_message() == "Hello from service"
