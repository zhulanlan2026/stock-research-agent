# Canary Rollout Runbook

- 通过 Feature Flag 控制灰度比例。
- 先 5% 流量，观察错误率 / 延迟 / HITL 指标。
- 无异常逐步提升到 25% / 50% / 100%。
- 保留 Shadow 或回滚开关。
- 记录每次变更的观测结果。
