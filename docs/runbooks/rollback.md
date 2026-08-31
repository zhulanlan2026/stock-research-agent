# Rollback Runbook

- 记录发布前版本 / 镜像 tag / 迁移版本。
- 数据库迁移使用可逆迁移，保留回滚脚本。
- 应用回滚：切换回上一镜像。
- 数据回滚：必要时从备份 / PITR 恢复。
- 回滚后运行 Golden Dataset 与关键 API 冒烟测试。
