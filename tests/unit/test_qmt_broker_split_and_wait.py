import time

import pytest


from bullet_trade.broker.qmt import QmtBroker


class DummyTrader:
    pass


@pytest.mark.asyncio
async def test_split_volume_and_async_wait(monkeypatch):
    broker = QmtBroker(account_id="test")
    broker._connected = True

    calls = []

    def fake_send_order(security, amount, price, side):
        calls.append((security, amount, price, side))
        return f"id_{len(calls)}"

    # 配置：每单最大 1000，异步等待（0）
    monkeypatch.setattr(
        "bullet_trade.utils.env_loader.get_live_trade_config",
        lambda: {"order_max_volume": 1000, "trade_max_wait_time": 0},
    )

    broker._send_order = fake_send_order  # type: ignore

    # 触发拆单：2500 = 1000 + 1000 + 500
    first_id = await broker.buy("000001.XSHE", amount=2500, price=10.0)
    assert first_id == "id_1"
    assert calls == [
        ("000001.SZ", 1000, 10.0, "buy"),
        ("000001.SZ", 1000, 10.0, "buy"),
        ("000001.SZ", 500, 10.0, "buy"),
    ]


@pytest.mark.asyncio
async def test_sync_wait_breaks_early(monkeypatch):
    broker = QmtBroker(account_id="test")
    broker._connected = True

    # 配置：同步等待 1s
    monkeypatch.setattr(
        "bullet_trade.utils.env_loader.get_live_trade_config",
        lambda: {"order_max_volume": 1000000, "trade_max_wait_time": 1},
    )

    # 立即返回已成，_maybe_wait 应很快退出
    async def _status(_oid):
        return {"status": "filled"}

    broker.get_order_status = _status  # type: ignore
    t0 = time.time()
    await broker._maybe_wait("abc")
    assert time.time() - t0 < 1.0


@pytest.mark.asyncio
async def test_zero_wait_override_skips_global_sync_wait(monkeypatch):
    broker = QmtBroker(account_id="test")
    broker._connected = True
    called = False

    monkeypatch.setattr(
        "bullet_trade.utils.env_loader.get_live_trade_config",
        lambda: {"order_max_volume": 1000000, "trade_max_wait_time": 16},
    )

    async def _status(_oid):
        nonlocal called
        called = True
        return {"status": "open"}

    broker.get_order_status = _status  # type: ignore
    t0 = time.time()
    await broker._maybe_wait("abc", override_timeout=0)
    assert time.time() - t0 < 0.2
    assert called is False


def test_qmt_symbol_mapping_roundtrip():
    broker = QmtBroker(account_id="test")
    assert broker._map_security("000001.XSHE") == "000001.SZ"
    assert broker._map_security("600000.XSHG") == "600000.SH"
    assert broker._map_to_jq_symbol("000001.SZ") == "000001.XSHE"
    assert broker._map_to_jq_symbol("300750.SZ") == "300750.XSHE"


def test_qmt_market_price_type_prefers_peer_price_for_both_markets():
    broker = QmtBroker(account_id="test")

    class Const:
        MARKET_PEER_PRICE_FIRST = 11
        MARKET_MINE_PRICE_FIRST = 12
        MARKET_SH_CONVERT_5_CANCEL = 13
        MARKET_SZ_CONVERT_5_CANCEL = 14
        ANY_PRICE = 15
        FIX_PRICE = 16

    assert broker._choose_market_price_type("600000.SH", Const) == Const.MARKET_PEER_PRICE_FIRST
    assert broker._choose_market_price_type("000001.SZ", Const) == Const.MARKET_PEER_PRICE_FIRST
    assert broker._choose_market_price_type("600000.XSHG", Const) == Const.MARKET_PEER_PRICE_FIRST
    assert broker._choose_market_price_type("000001.XSHE", Const) == Const.MARKET_PEER_PRICE_FIRST
    assert broker._choose_market_price_type("430047.BJ", Const) == Const.MARKET_PEER_PRICE_FIRST


def test_qmt_market_price_type_falls_back_to_exchange_specific_five_cancel():
    broker = QmtBroker(account_id="test")

    class Const:
        MARKET_PEER_PRICE_FIRST = None
        MARKET_MINE_PRICE_FIRST = None
        MARKET_SH_CONVERT_5_CANCEL = 13
        MARKET_SZ_CONVERT_5_CANCEL = 14
        ANY_PRICE = 15
        FIX_PRICE = 16

    assert broker._choose_market_price_type("600000.SH", Const) == Const.MARKET_SH_CONVERT_5_CANCEL
    assert broker._choose_market_price_type("000001.SZ", Const) == Const.MARKET_SZ_CONVERT_5_CANCEL
    assert broker._choose_market_price_type("430047.BJ", Const) == Const.MARKET_SH_CONVERT_5_CANCEL
