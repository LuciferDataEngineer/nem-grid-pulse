import httpx
import pytest

from nem_grid_pulse.http_client import (
    MissingDatasetError,
    SourceUnavailableError,
    UnexpectedStatusError,
    fetch_bytes,
)
from nem_grid_pulse.settings import iter_months, price_url
from nem_grid_pulse.watermark import should_skip


class _Response:
    def __init__(self, status_code: int, content: bytes = b"ok"):
        self.status_code = status_code
        self.content = content


class _Client:
    def __init__(self, statuses: list[int]):
        self._statuses = list(statuses)
        self.calls = 0

    def get(self, url: str) -> _Response:
        self.calls += 1
        return _Response(self._statuses.pop(0))


def test_fetch_retries_then_returns_the_body():
    client = _Client([503, 503, 200])
    slept: list[float] = []
    body = fetch_bytes("https://example.test/a", client, sleep=slept.append, backoff_seconds=0.1)
    assert body == b"ok"
    assert slept == [0.1, 0.2]
    assert client.calls == 3


def test_fetch_does_not_retry_a_missing_file():
    client = _Client([404, 200])
    with pytest.raises(MissingDatasetError):
        fetch_bytes("https://example.test/missing", client, sleep=lambda _seconds: None)
    assert client.calls == 1


def test_fetch_does_not_retry_a_client_error():
    client = _Client([400])
    with pytest.raises(UnexpectedStatusError):
        fetch_bytes("https://example.test/bad", client, sleep=lambda _seconds: None)
    assert client.calls == 1


def test_fetch_gives_up_when_the_source_stays_down():
    client = _Client([503, 503, 503, 503])
    with pytest.raises(SourceUnavailableError):
        fetch_bytes("https://example.test/down", client, sleep=lambda _seconds: None)
    assert client.calls == 4


def test_month_window_is_thirty_six_months():
    months = iter_months("202311", "202610")
    assert months[0] == "202311"
    assert months[-1] == "202610"
    assert len(months) == 36


def test_price_url_uses_the_public_aemo_filename():
    url = price_url("NSW1", "202509")
    assert url.endswith("/PRICE_AND_DEMAND_202509_NSW1.csv")
    assert url.startswith("https://www.aemo.com.au/aemo/data/nem/priceanddemand/")


def test_complete_watermark_is_skipped_until_forced():
    watermarks = {"price_demand": {"NSW1|202311": {"complete": True}}}
    assert should_skip(watermarks, "price_demand", "NSW1|202311", force=False)
    assert not should_skip(watermarks, "price_demand", "NSW1|202311", force=True)
    assert not should_skip(watermarks, "price_demand", "NSW1|202312", force=False)
    partial = {"price_demand": {"NSW1|202610": {"complete": False}}}
    assert not should_skip(partial, "price_demand", "NSW1|202610", force=False)


def test_transport_errors_are_retried(monkeypatch):
    class Broken:
        calls = 0

        def get(self, url: str):
            self.calls += 1
            if self.calls < 2:
                raise httpx.ConnectError("down")
            return _Response(200, b"back")

    client = Broken()
    assert fetch_bytes("https://example.test/a", client, sleep=lambda _seconds: None) == b"back"
