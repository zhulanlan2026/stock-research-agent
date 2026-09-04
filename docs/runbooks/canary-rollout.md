# Canary Rollout Runbook

- 通过 Feature Flag 控制灰度比例。
- 先 5% 流量，观察错误率 / 延迟 / HITL 指标。
- 无异常逐步提升到 25% / 50% / 100%。
- 保留 Shadow 或回滚开关。
- 记录每次变更的观测结果。

## 放量决策

`FeatureFlagService.is_enabled(key, tenant_id=..., user_id=..., now=...)` 按以下顺序决策：

1. `kill_switch` 开启 → 立即全量关闭（回滚）。
2. 全局 `enabled` → 全量开启（100%）。
3. `user_allowlist` → 白名单用户开启。
4. `tenant_allowlist` → 白名单租户开启。
5. `start_at` / `end_at` 时间窗口外 → 关闭。
6. `percentage` 放量：按 `sha256(key:user_id)` 取模 100，落在 `[0, percentage)` 则开启。

## 放量节奏

```text
shadow -> internal allowlist -> 1% -> 5% -> 20% -> 50% -> 100%
```

## 回滚

- 立即回滚：打开 `kill_switch`，或把 `percentage` 设为 0。
- 逐步回滚：把 `percentage` 逐级下调。
- 白名单不随 percentage 关闭，用于内部验证时需单独清空。
