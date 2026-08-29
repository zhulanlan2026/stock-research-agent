import subprocess
from pathlib import Path

import pytest

from stock_research.documents.parsers.mineru import (
    MinerUPdfParser,
    ParserUnavailableError,
)


def test_mineru_parser_detects_unavailable_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda binary: None)

    assert MinerUPdfParser().is_available() is False
    with pytest.raises(ParserUnavailableError):
        MinerUPdfParser().parse(b"%PDF-1.4", "report.pdf")


def test_mineru_parser_runs_cli_and_reads_markdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda binary: "/usr/bin/mineru")

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        output_dir = Path(args[3])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "report.md").write_text("# Parsed", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    assert MinerUPdfParser().parse(b"%PDF-1.4", "report.pdf") == "# Parsed"
