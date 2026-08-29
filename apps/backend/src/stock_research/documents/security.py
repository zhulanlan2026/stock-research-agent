from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".html",
    ".htm",
    ".csv",
    ".txt",
    ".md",
}

DENIED_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".dll",
    ".so",
    ".js",
    ".ps1",
}

MAX_FILE_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class FileSecurityResult:
    allowed: bool
    content_hash: str
    sanitized_filename: str
    reason: str | None = None


class FileSecurityService:
    """上传文件安全策略，后续可替换恶意文件扫描实现。"""

    def validate(
        self,
        filename: str | None,
        content_type: str | None,
        data: bytes,
    ) -> FileSecurityResult:
        sanitized_filename = Path(filename or "upload").name
        content_hash = hashlib.sha256(data).hexdigest()
        suffix = Path(sanitized_filename).suffix.lower()

        if len(data) > MAX_FILE_BYTES:
            return FileSecurityResult(
                allowed=False,
                content_hash=content_hash,
                sanitized_filename=sanitized_filename,
                reason="文件超过 100MB 限制",
            )
        if suffix in DENIED_EXTENSIONS:
            return FileSecurityResult(
                allowed=False,
                content_hash=content_hash,
                sanitized_filename=sanitized_filename,
                reason=f"禁止上传可执行文件类型: {suffix}",
            )
        if suffix not in ALLOWED_EXTENSIONS:
            return FileSecurityResult(
                allowed=False,
                content_hash=content_hash,
                sanitized_filename=sanitized_filename,
                reason=f"不支持的文件类型: {suffix or 'unknown'}",
            )

        return FileSecurityResult(
            allowed=True,
            content_hash=content_hash,
            sanitized_filename=sanitized_filename,
        )
