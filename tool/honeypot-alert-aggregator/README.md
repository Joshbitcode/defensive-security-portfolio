# honeypot-alert-aggregator（hpa）

> 防御向小工具。**代码由仓库所有者编写，本文档只提供定位、设计、目录结构与用法约定；文中示例输出均为演示格式，不是真实运行结果。**

## 功能定位

**蜜罐告警聚合**：把多个蜜罐节点（如 cowrie、dionaea 及各类低交互蜜罐）上报的告警统一接入，做三件事：

1. **归一化**：不同蜜罐的原始日志 → 统一告警结构；
2. **去重**：同源、同类、同载荷的重复告警在时间窗口内合并（扫描器与重放流量会产生大量噪声）；
3. **聚合**：按时间窗口/来源 IP 汇总，输出摘要报告（明细、按源 IP 统计、跨节点命中提示）。

典型使用场景：个人或小团队运行 2–5 个蜜罐节点，每天收到成百上千条告警，需要快速回答三个问题——**谁在打我？在打什么？哪些值得我人工看？**

## 技术栈选型

| 层 | 选择 | 理由 |
|---|---|---|
| 语言 | Python ≥ 3.10 | 生态成熟、部署简单，与蜜罐工具链同语言 |
| CLI | argparse（标准库） | 零依赖 |
| 配置 | TOML（标准库 tomllib，需 Python ≥ 3.11） | 人类可读、机器可写 |
| 存储 | sqlite3（标准库） | 单文件、无服务、重启不丢状态 |
| 去重/载荷摘要 | hashlib | 载荷哈希作为去重键的一部分 |
| 可选富化 | geoip2（optional extra） | 只做"可选"，不设为默认依赖 |
| 输出 | 文本表格 / JSON / CSV（标准库 csv、json） | 人看文本，机器接 JSON |

原则：**标准库优先，重型依赖为可选 extra**。这个工具的价值在"聚合逻辑正确"而不是依赖多。

## 目录结构

```text
honeypot-alert-aggregator/
├── README.md                  # 本文件
├── DESIGN.md                  # 设计评审文档
├── config.example.toml        # 配置示例
├── samples/
│   └── alerts.jsonl           # 示例告警（合成数据，非真实攻击流量）
├── src/
│   └── hpa/
│       ├── __init__.py
│       ├── __main__.py        # python -m hpa 入口
│       ├── cli.py             # argparse 子命令
│       ├── config.py          # TOML 读取与校验
│       ├── models.py          # 统一告警结构（dataclass）
│       ├── adapters/          # 各蜜罐格式 → 统一结构
│       │   ├── __init__.py
│       │   └── generic_jsonl.py
│       ├── dedup.py           # 复合键 + 时间窗口去重（纯函数优先）
│       ├── aggregate.py       # 时间桶/按源 IP 聚合（纯函数优先）
│       ├── store.py           # sqlite3 读写
│       └── report.py          # 文本/JSON/CSV 输出
└── tests/
    ├── test_dedup.py          # 去重逻辑单测（样例数据）
    └── test_aggregate.py      # 聚合逻辑单测
```

## 用法示例

以下命令形态为**接口约定**，具体行为以实现为准；示例输出为演示格式。

```bash
# 安装（可选，装了之后直接敲 hpa；不装也可用 PYTHONPATH=src python -m hpa）
pip install -e .

# 接入一条或多条告警（JSON Lines，不带文件参数则读 stdin）
python -m hpa ingest samples/alerts.jsonl

# 查看最近 24 小时汇总：按来源 IP、事件类型、蜜罐节点统计
python -m hpa report --last 24 --format text

# 指定显式时间窗口（适合回溯历史告警）
python -m hpa report --since 2026-02-01T00:00:00Z --until 2026-02-02T00:00:00Z

# 导出机器可读报告
python -m hpa report --last 168 --format json -o report.json

# 查看去重与存储状态
python -m hpa status
```

```text
[示例输出 · 非真实运行结果]
Report window: 2026-02-01T00:00:00Z ~ 2026-02-02T00:00:00Z
unique events (after dedup): 17   raw events: 1,204

top source IPs:
  203.0.113.42   conn=812  events=3  honeypots=2/3  [ssh-auth, ssh-auth, scp-download]
  198.51.100.7   conn=47   events=1  honeypots=1/3  [http-scan]
```

## 告警输入格式约定

统一抽象层（`models.py`）字段约定：

```json
{"ts": "2026-02-01T12:34:56Z", "src_ip": "203.0.113.42", "src_port": 48123,
 "dst_ip": "192.0.2.10", "dst_port": 2222, "honeypot": "ssh-01",
 "event_type": "ssh-auth", "payload_hash": "<sha256 前缀，可选>", "raw": "..."}
```

`samples/alerts.jsonl` 提供一批**合成示例**（RFC 5737 文档地址段），仅用于测试聚合逻辑。

## 设计要点（详见 DESIGN.md）

- 去重键 = `(src_ip, dst_port, honeypot, event_type, payload_hash)` + 时间窗口（默认 300 s，可配）；
- **跨节点命中提示**：同一来源 IP 出现在多个蜜罐节点，自动标记为"值得人工关注"；
- 纯函数优先：去重/聚合逻辑不碰 IO，便于单测与评审。

## 状态与边界

- 代码已实现（v0.1，Python ≥ 3.11，标准库 only），单元测试 6/6 通过；下面"验证过的运行输出"一节是对 `samples/alerts.jsonl`（合成数据）的真实运行结果；
- 本工具是**学习型防御工具**，不替代 SIEM/SOAR，不承诺处理大规模生产流量；
- 若接入真实蜜罐数据，请自查当地法律与蜜罐部署的合规边界（仅部署在自有资产上）。

## 验证过的运行输出（真实测试运行，输入为合成样例）

```text
$ python -m hpa --db tmp-e2e.db ingest samples/alerts.jsonl
ingested: new=4 duplicates=1 skipped=0 (window=300s, db=tmp-e2e.db)

$ python -m hpa --db tmp-e2e.db report --since 2026-02-01T00:00:00Z --until 2026-02-02T00:00:00Z
Report window: 2026-02-01T00:00:00+00:00 ~ 2026-02-02T00:00:00+00:00 (explicit range)
unique events (after dedup): 4   sources: 2

top source IPs:
      203.0.113.42  events=3    honeypots=2  [ssh-authx2, login-attemptx1] [cross-node]
      198.51.100.7  events=1    honeypots=1  [http-scanx1]
```

解读：5 条原始告警中 1 条被 300 s 窗口去重；203.0.113.42 同时命中 ssh-01 与 telnet-02 两个蜜罐，被标记 `[cross-node]` 并置顶——这正是设计目标"谁值得人工看"。

## 运行测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -v   # 6 个用例，全过
```
