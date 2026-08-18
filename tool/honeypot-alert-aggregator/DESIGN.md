# DESIGN.md — 蜜罐告警聚合器设计评审

> 目的：在写代码前把关键决策写下来，让实现阶段少返工。本文档面向代码评审者与未来的自己。

## 1. 需求与非目标

**需求（Must）**

1. 接受多个来源的告警（JSON Lines 输入，适配器可扩展），归一化为统一结构；
2. 时间窗口去重：同源、同类、同载荷的重复告警合并；
3. 时间桶聚合：按小时/天输出摘要；按来源 IP 统计连接数、事件类型分布、命中蜜罐数；
4. 输出三种格式：文本（人看）、JSON/CSV（机器用）；
5. 状态持久化到 sqlite3 单文件，重启不丢。

**非目标（Not now）**

- 不做实时流式处理（先做批量 ingest/report）；
- 不接 SIEM（如 Elasticsearch/Splunk），只输出标准格式留接口；
- 不做告警自动响应（封禁、联动防火墙）——那是 SOAR 的范畴；
- 不内置武器化检测规则库（先做聚合，检测规则留给后续）。

## 2. 数据流

```text
蜜罐节点日志 ──► 适配器(adapter) ──► 统一告警(models) ──► 去重(dedup)
                                                          │
报告(report) ◄── 聚合(aggregate) ◄── 存储(store/sqlite3) ◄─┘
```

- **适配器**：只负责"翻译"，不负责判断；新增蜜罐类型 = 新增一个适配器文件。
- **去重**：无状态纯函数，输入统一告警流，输出"是否为新事件"。
- **聚合**：纯函数，读一批事件，输出统计结构；由 report 命令决定窗口。
- **存储**：唯一有 IO 的模块，表结构见 §4。

## 3. 去重设计（本工具的核心决策）

### 3.1 复合键

```text
dedup_key = sha256(src_ip | dst_port | honeypot | event_type | payload_hash)[:16]
```

- **为什么含 payload_hash**：扫描器/蠕虫对同一端口反复重放相同载荷，只按五元组去重会把这些噪声当新事件；载荷哈希让"同一行为"真正合并。
- **为什么含 honeypot**：同一行为打到两个节点，是两个节点各自的观测，去重不跨节点（跨节点反而要在聚合层高亮）。
- **不含时间**：时间由窗口机制处理，键本身时间无关。

### 3.2 时间窗口

- 默认固定窗口 300 s（可配），实现上记录"事件最后一次出现时间"，采用**带过期滑动的最近一次出现**（last-seen + TTL）而非严格滑窗计数：实现简单、内存有界、对"持续几分钟的扫描"也能合并。
- 取舍记录：严格滑动窗口（如 5 分钟精确计数）需要保留窗口内所有事件，批量 ingest 场景收益低，故不做。

## 4. 存储表结构（sqlite3）

```sql
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,               -- ISO8601 UTC
  src_ip TEXT NOT NULL,
  src_port INTEGER,
  dst_ip TEXT NOT NULL,
  dst_port INTEGER,
  honeypot TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload_hash TEXT,
  dedup_key TEXT NOT NULL,
  raw TEXT
);
CREATE INDEX idx_events_ts ON events(ts);
CREATE INDEX idx_events_dedup ON events(dedup_key, ts);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);  -- schema 版本等
```

设计点：`raw` 保存原始行，保证任何聚合结论都能回溯到原始告警（可验证性的来源）。

## 5. 聚合规则

1. **时间桶**：UTC 小时桶与天桶，避免本地时区歧义；
2. **按源 IP 指标**：连接数、去重后事件数、事件类型分布、命中蜜罐数、首末次出现时间；
3. **跨节点命中提示**：`honeypots_hit ≥ 2` 的源 IP 在报告中置顶并标记 `[cross-node]`——同一来源同时扫多个蜜罐，通常是值得人工看的信号；
4. **输出排序**：先按跨节点标记，再按事件数降序。

## 6. 配置（config.example.toml）

```toml
[dedup]
window_seconds = 300

[store]
path = "hpa.db"

[report]
default_window_hours = 24
top_n = 20
```

## 7. 测试策略

- **纯函数单测优先**：dedup 与 aggregate 不依赖 IO，用 `samples/alerts.jsonl` 构造用例（例如：同键两条告警 → 1 条新事件；跨节点同源 → 标记 cross-node）；
- **CLI 冒烟测试**：ingest 样例文件 → report 输出非空、格式合法（JSON 可解析）；
- **不做**：真实蜜罐流量测试（部署环境不具备，也不在本文档承诺范围内）。

## 8. 演进路线（记录，不承诺）

1. 更多适配器：cowrie JSON、dionaea 上报格式；
2. 可选 geoip2 富化（源 IP 地理信息，仅标注，不参与去重）；
3. Webhook 输出（新事件即时推送）；
4. 规则引擎：基于事件类型/频率的简单检测规则（如"同一 IP 5 分钟内 ssh-auth 失败 ≥ 50 次"）。

## 9. 评审结论

- 设计取舍合理：标准库优先、纯函数核心、sqlite 持久化，适合作为学习型防御工具的第一个版本；
- 最需要谨慎实现的部分是 **dedup 键与窗口语义**（§3）——它决定工具输出"够不够安静、会不会漏掉真信号"；
- 明确边界：本工具只做聚合与呈现，不替代 SIEM，不承诺生产规模性能。
