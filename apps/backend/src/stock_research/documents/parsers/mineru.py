from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

MINERU_PARSER_VERSION = "mineru:3.4.5"


class ParserUnavailableError(RuntimeError):
    pass


class MinerUPdfParser:
    """调用 MinerU CLI 解析 PDF，返回 Markdown 文本。"""

    version = MINERU_PARSER_VERSION

    def __init__(self, binary: str = "mineru", timeout_seconds: int = 300) -> None:
        self.binary = binary
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        return shutil.which(self.binary) is not None

    def parse(self, data: bytes, filename: str) -> str:
        if not self.is_available():
            raise ParserUnavailableError(
                f"{self.binary} is not installed; cannot parse PDF with MinerU"
            )

        with TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            input_path = tmp_dir / (Path(filename).name or "document.pdf")
            output_dir = tmp_dir / "out"
            input_path.write_bytes(data)
            output_dir.mkdir()

            result = subprocess.run(
                [
                    self.binary,
                    str(input_path),
                    "--output-dir",
                    str(output_dir),
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"mineru parse failed: {result.stderr.strip()}"
                )

            markdown_files = list(output_dir.rglob("*.md"))
            if not markdown_files:
                raise RuntimeError("mineru produced no markdown output")
            return markdown_files[0].read_text(encoding="utf-8")
