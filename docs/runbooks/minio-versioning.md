# MinIO Versioning Runbook

## 启用版本化

使用 `mc` 命令行：

```bash
mc alias set local http://localhost:9000 minioadmin minioadmin123
mc version enable local/raw-documents
```

## 验证

```bash
mc version info local/raw-documents
```

## 恢复历史版本

```bash
mc ls --versions local/raw-documents/object-key
mc cp --version-id VERSION_ID local/raw-documents/object-key local/raw-documents/restored-object
```

## 说明

- 原始文件按不可变版本保存。
- 修订上传创建新版本，不覆盖旧版本。
- 删除默认创建 delete marker，历史版本仍可恢复。
