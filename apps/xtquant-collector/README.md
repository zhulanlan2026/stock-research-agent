# xtquant-collector

Windows 原生 MiniQMT/XTQuant 采集器，按 V2.0 技术方案第 13 章实现。

当前支持：

- XTQuant 实时行情
- XTQuant 历史 K 线
- XTQuant 公告采集
- 本地 JSON Lines 真实财务事实采集

## 真实财务事实格式

启用财务采集后，将 JSON Lines 文件放到
`COLLECTOR_FINANCIAL_DATA_PATH` 指定的路径，每行一条事实：

```json
{"symbol":"600519.SH","metric":"revenue","period":"2025Q4","value":"1200.00","unit":"CNY","source_id":"real-source","disclosed_at":1767225600000,"available_at":1767225600000}
```

相关环境变量：

```env
COLLECTOR_COLLECT_FINANCIAL_ENABLED=true
COLLECTOR_FINANCIAL_DATA_PATH=./data/financial-facts.jsonl
```
