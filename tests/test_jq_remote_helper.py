import pytest

from helpers import bullet_trade_jq_remote_helper as helper
from tests.test_remote_server import stub_server  # 复用 stub server fixture


def test_helper_restores_legacy_stringified_tuple_columns():
    payload = {
        "dtype": "dataframe",
        "columns": [
            "('600635.XSHG', 'time')",
            "('600635.XSHG', 'open')",
            "('000001.XSHG', 'open')",
        ],
        "records": [[1777392000000.0, 5.4, 4061.822]],
    }

    df = helper._df_from_payload(payload)

    assert isinstance(df.columns, helper.pd.MultiIndex)
    assert df.columns.names == ["field", "code"]
    assert list(df.columns) == [
        ("time", "600635.XSHG"),
        ("open", "600635.XSHG"),
        ("open", "000001.XSHG"),
    ]
    assert df["open"]["600635.XSHG"].iloc[0] == 5.4


def test_helper_e2e_with_stub(stub_server):
    helper.configure(
        host=stub_server.listen,
        port=stub_server.port,
        token=stub_server.token,
        account_key=stub_server.accounts[0].key if stub_server.accounts else "default",
    )
    # 账户与持仓
    account = helper.get_account()
    assert account.available_cash == 1_000_000
    positions = helper.get_positions()
    assert positions == []

    # 下单（限价 / 自动补价市价）
    oid = helper.order("000001.XSHE", 100, price=10.0, wait_timeout=0)
    assert oid
    status = helper.get_order_status(oid)
    assert status.get("order_id") == oid

    open_orders = helper.get_open_orders()
    assert oid in open_orders
    orders = helper.get_orders(order_id=oid)
    assert oid in orders
    trades = helper.get_trades(order_id=oid)
    assert isinstance(trades, dict)

    cancel_resp = helper.cancel_order(oid)
    assert cancel_resp.get("value") is True or cancel_resp.get("success", True) is True
