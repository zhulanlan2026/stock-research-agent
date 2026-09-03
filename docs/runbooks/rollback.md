# Rollback Runbook

- 记录发布前版本 / 镜像 tag / 迁移版本。
- 数据库迁移使用可逆迁移，保留回滚脚本。
- 应用回滚：切换回上一镜像。
- 数据回滚：必要时从备份 / PITR 恢复。
- 回滚后运行 Golden Dataset 与关键 API 冒烟测试。

## 应用回滚（切换到指定镜像 tag）

镜像 tag 即 commit SHA（`cd.yml` 每次推送 `:latest` 和 `:${github.sha}`）。回滚就是部署上一个 SHA：

```bash
cd "$DEPLOY_PATH"
export GITHUB_REPOSITORY=zhulanlan2026/stock-research-agent
export IMAGE_TAG=<上一个 commit SHA>
./scripts/deploy.sh
```

或通过 GitHub Actions 手动部署：`Actions → Deploy → Run workflow`，在 `image_tag` 输入框填上一个 SHA。

查看当前运行的镜像 tag：

```bash
docker ps --filter name=research --format '{{.Names}}\t{{.Image}}'
```
