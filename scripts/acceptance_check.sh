#!/usr/bin/env bash
set -uo pipefail

cd "$(dirname "$0")/.."

PASSED=0
FAILED=0

check() {
  local name="$1"
  shift
  echo ""
  echo "▶ ${name}"
  if "$@"; then
    echo "  ✅ 通过"
    PASSED=$((PASSED + 1))
  else
    echo "  ❌ 失败"
    FAILED=$((FAILED + 1))
  fi
}

echo "===== 第 1 层：自动化检查 ====="
check "后端 + 采集器单测" .venv/bin/python -m pytest apps/backend/tests apps/xtquant-collector/tests -q
check "ruff" .venv/bin/python -m ruff check .
check "mypy" .venv/bin/python -m mypy .
check "前端 typecheck" pnpm --filter @stock-research/web typecheck
check "前端 test" pnpm --filter @stock-research/web test

echo ""
echo "===== 第 2 层：真实存储集成 ====="
check "Neo4j 集成" .venv/bin/python -m pytest tests/integration/test_neo4j_publish.py -q
check "Milvus 集成" .venv/bin/python -m pytest tests/integration/test_milvus_dense.py -q
check "embedding 验证" .venv/bin/python scripts/verify_embedding.py

echo ""
echo "结果：${PASSED} 通过，${FAILED} 失败"
if [ "$FAILED" -eq 0 ]; then
  echo "✅ 全部验收通过"
else
  echo "❌ 存在失败项"
  exit 1
fi
