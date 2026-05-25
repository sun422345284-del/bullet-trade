"""
异步调度器在同一分钟触发多个任务的回归测试。
"""

import datetime as dt
from types import SimpleNamespace

import pytest

from bullet_trade.core.async_engine import AsyncBacktestEngine
from bullet_trade.core.async_scheduler import AsyncScheduler
from bullet_trade.core.settings import reset_settings, set_option


@pytest.fixture(autouse=True)
def _reset_settings():
    reset_settings()
    yield
    reset_settings()


@pytest.mark.asyncio
async def test_async_scheduler_runs_all_tasks_in_same_minute(monkeypatch):
    """同一分钟注册的不同任务都应被触发。"""
    set_option('backtest_frequency', 'minute')

    periods = [(dt.time(9, 30), dt.time(11, 30)), (dt.time(13, 0), dt.time(15, 0))]
    trade_day = dt.date(2025, 1, 3)
    open_dt = dt.datetime.combine(trade_day, periods[0][0])
    current_dt = dt.datetime(2025, 1, 3, 9, 34)

    engine = AsyncBacktestEngine()
    engine.frequency = 'minute'
    is_bar = engine._is_bar_time(current_dt, periods, open_dt)
    assert is_bar

    fired = []

    def bar_task(context):
        fired.append('bar')

    def explicit_task(context):
        fired.append('explicit')

    scheduler = AsyncScheduler()
    scheduler.run_daily(bar_task, 'every_bar')
    scheduler.run_daily(explicit_task, '09:34')

    context = SimpleNamespace(previous_date=None)
    monkeypatch.setattr('bullet_trade.core.async_scheduler.get_market_periods', lambda: periods)

    await scheduler.trigger(current_dt, context, is_bar=is_bar)

    assert fired == ['bar', 'explicit']


def test_async_backtest_engine_daily_frequency_every_bar_is_trading_minute():
    """异步回测的 every_bar 判定不应因日频回测退化为开盘一次。"""
    periods = [(dt.time(9, 30), dt.time(11, 30)), (dt.time(13, 0), dt.time(15, 0))]
    trade_day = dt.date(2025, 1, 3)
    open_dt = dt.datetime.combine(trade_day, periods[0][0])

    engine = AsyncBacktestEngine()
    engine.frequency = 'daily'

    assert engine._is_bar_time(dt.datetime(2025, 1, 3, 9, 34), periods, open_dt)
    assert engine._is_bar_time(dt.datetime(2025, 1, 3, 14, 59), periods, open_dt)
    assert not engine._is_bar_time(dt.datetime(2025, 1, 3, 11, 30), periods, open_dt)
