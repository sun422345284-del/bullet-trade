# 实盘引擎

这页只讲最常见的两种实盘方式：

- 本地 QMT
- 远程 qmt-remote

## 1. 本地 QMT 最小配置

`.env` 最少只写这几个：

```env
DEFAULT_DATA_PROVIDER=qmt
DEFAULT_BROKER=qmt
QMT_DATA_PATH=C:\国金QMT交易端\userdata_mini
QMT_ACCOUNT_ID=123456
```

运行：

```bash
bullet-trade live strategies/demo_strategy.py --broker qmt
```

说明：

- 股票账户默认就是 `stock`，所以 `QMT_ACCOUNT_TYPE` 不用写
- 只有期货账户才需要写 `QMT_ACCOUNT_TYPE=future`

## 2. 远程 qmt-remote 最小配置

如果 QMT 在另一台 Windows 机器上，客户端 `.env` 只要：

```env
DEFAULT_DATA_PROVIDER=qmt-remote
DEFAULT_BROKER=qmt-remote
QMT_SERVER_HOST=10.0.0.8
QMT_SERVER_PORT=58620
QMT_SERVER_TOKEN=secret
```

运行：

```bash
bullet-trade live strategies/demo_strategy.py --broker qmt-remote
```

单账户时，不用写 `QMT_SERVER_ACCOUNT_KEY`。

## 3. 远程 server 怎么启动

Windows 服务端 `.env`：

```env
QMT_DATA_PATH=C:\国金QMT交易端\userdata_mini
QMT_ACCOUNT_ID=123456
QMT_SERVER_TOKEN=secret
```

启动：

```bash
bullet-trade --env-file .env server --listen 0.0.0.0 --port 58620 --enable-data --enable-broker
```

更完整的说明看 [QMT server](qmt-server.md)。

## 4. 多账户时再看这两个参数

### server 端

多账户时才用 `--accounts`。  
股票账户示例：

```bash
--accounts main=123456
```

期货账户示例：

```bash
--accounts hedge=654321:future
```

### 客户端

多账户时，客户端才需要：

```env
QMT_SERVER_ACCOUNT_KEY=main
```

## 5. 模拟盘/实盘切换检查

模拟盘和实盘应尽量使用同一份策略代码，只通过 `.env` 切换账户、网关地址和风控参数。切换前先确认这几件事：

| 检查项 | 模拟盘 | 实盘 |
|--------|--------|------|
| QMT 账号 | 仿真或测试资金号 | 真实资金号 |
| bullet-trade server | 默认 `58620`，提供行情和交易能力 | 默认 `58620`，提供行情和交易能力 |
| 上层调度网关 | 如使用上层网关，策略通常连接网关自己的端口 | 同样连接上层网关端口，再由网关连接 bullet-trade server |
| 下单等待 | 可用 `TRADE_MAX_WAIT_TIME=0` 压测异步链路 | 建议保留同步等待或按单设置 `wait_timeout` |
| 风控 | 先放宽，确认链路能跑通 | 再启用 `RISK_CHECK_ENABLED`、`MIN_BUY_ORDER_VALUE` 等 |

不要把 `QMT_SERVER_PORT` 和上层调度网关端口混用：`QMT_SERVER_PORT` 是 bullet-trade server 的端口；上层网关自己的端口应写在上层系统配置里。

## 6. 下单等待（同步/异步）

实盘下单时，引擎默认会**同步等待最多 16 秒**再返回结果。可以通过两种方式调整：

| 方式 | 说明 |
|------|------|
| `.env` 设置 `TRADE_MAX_WAIT_TIME` | 全局生效，默认 `16`；设 `0` 为纯异步 |
| 函数参数 `wait_timeout=10` | 单次下单覆盖，优先级高于环境变量 |

策略中批量异步下单示例：

```python
order_target('000001.XSHE', 0, wait_timeout=0)   # 立即返回
order('600519.XSHG', 100, wait_timeout=10)         # 等 10 秒
```

## 7. 常见问题

### 为什么文档里不再写一大堆 `.env`

因为绝大多数参数都有默认值。  
第一步应该先跑通最小链路，不要一开始就把日志、风控、后台任务、通知全部写进去。

正式实盘如果账号没有免五，建议在开启风控后按需配置 `MIN_BUY_ORDER_VALUE`，例如 `MIN_BUY_ORDER_VALUE=1000`。默认值为 `0`，不限制买入小单；该规则只拦截买入，不影响卖出或清仓。

### `:stock` 要不要写

单账户股票场景不用写。  
默认就是 `stock`。

### `--data-path` 为什么不能写

因为当前版本没有这个 CLI 参数。  
数据目录要写在 `.env` 的 `QMT_DATA_PATH`。

### 运行态目录和日志目录要不要先配

先不用。  
除非你有明确的目录要求，否则先用默认值即可。
