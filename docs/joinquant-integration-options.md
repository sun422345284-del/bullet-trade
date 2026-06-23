# 聚宽策略接入 BulletTrade：两种方案对比

这页用于帮用户选择“怎么改聚宽策略”。两种方案都需要先完成同一个前置条件：Windows 机器上 QMT 已登录，`bullet-trade server` 已启动，并且聚宽研究根目录已上传 `bullet_trade_jq_remote_helper.py`。

## 两种方案

| 方案 | 改法 | 适合谁 |
| --- | --- | --- |
| [方案 A：显式调用 helper](joinquant-helper-explicit.md) | 下单处改成 `bt.order(...)`、`bt.order_target_value(...)` 等 | 已经改过策略、只想少量远程下单、希望每个真实下单点都非常明确 |
| [方案 B：接管聚宽函数](joinquant-live-takeover-usage.md) | 在 `process_initialize` 安装兼容层，原来的 `order(...)`、`context.portfolio` 尽量不改 | 存量聚宽策略、下单点多、现金和持仓判断也想跟真实账户一致 |

## 方案 A：显式调用 helper

策略里显式导入 helper，并在下单处写 `bt.xxx`：

```python
import bullet_trade_jq_remote_helper as bt


def process_initialize(context):
    bt.configure(
        host="your.server.ip",
        port=58620,
        token="secret",
    )


def handle_data(context, data):
    bt.order_target_value("510300.XSHG", 100000)
```

优点：

- 每一个真实下单点都很清楚。
- 适合 notebook、研究环境、最小联调和已经改好的老策略。
- 不覆盖聚宽原始函数，行为更显式。

缺点：

- 原策略里每个下单点都要改成 `bt.xxx`。
- 如果策略用 `context.portfolio.available_cash`、`context.portfolio.positions` 做仓位判断，仍然读的是聚宽虚拟盘账本，可能和远程真实账户不一致；这类地方也要同步改成远程账户读取。

详细步骤见 [方案 A：显式调用 helper](joinquant-helper-explicit.md)。

## 方案 B：接管聚宽函数

策略只在 `process_initialize` 安装一次兼容层：

```python
import bullet_trade_jq_remote_helper as bt


BT_REMOTE_HOST = "your.server.ip"
BT_REMOTE_PORT = 58620
BT_REMOTE_TOKEN = "secret"


def process_initialize(context):
    bt.install_jq_compat(
        globals(),
        context=context,
        host=BT_REMOTE_HOST,
        port=BT_REMOTE_PORT,
        token=BT_REMOTE_TOKEN,
        mirror_jq_orders=False,
        default_wait_timeout=16,
    )
```

安装后，模拟盘里这些写法会走 BulletTrade 远程真实账户：

```python
context.portfolio.available_cash
context.portfolio.total_value
context.portfolio.positions

order("000001.XSHE", 100)
order_target_value("510300.XSHG", 100000)
order_target_percent("510300.XSHG", 0.2)
```

优点：

- 原策略改动最少。
- 现金、总资产、持仓和下单使用同一个远程真实账户口径。
- 下单点多、按比例调仓多的聚宽策略更适合这个方案。

缺点：

- 属于函数接管，行为比显式 `bt.xxx` 更“自动”。
- 第一版只支持股票/ETF 多头常见交易函数；不支持 `side="short"`、`pindex!=0`、`close_today=True` 和停止单。
- 真实交易建议保持 `mirror_jq_orders=False`，所以聚宽虚拟盘页面的持仓和收益曲线不再代表真实账户。

详细步骤见 [方案 B：接管聚宽函数](joinquant-live-takeover-usage.md)。

## 推荐选择

默认建议：

- 新用户先用方案 A 在聚宽研究里验证 server、token、账户和持仓能查通。
- 正式迁移存量聚宽模拟盘策略时，优先用方案 B。
- 如果策略只在一两个地方发单，并且不依赖聚宽 `context.portfolio` 做真实仓位判断，方案 A 也可以长期使用。

无论选择哪种方案，第一次真实联调都先查账户和持仓，再做小金额测试单。
