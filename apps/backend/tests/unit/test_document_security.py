from stock_research.documents.security import FileSecurityService


def test_file_security_allows_supported_document() -> None:
    result = FileSecurityService().validate(
        "report.pdf",
        "application/pdf",
        b"%PDF-1.4",
    )

    assert result.allowed is True
    assert result.sanitized_filename == "report.pdf"
    assert result.content_hash


def test_file_security_rejects_executable() -> None:
    result = FileSecurityService().validate(
        "evil.exe",
        "application/octet-stream",
        b"MZ",
    )

    assert result.allowed is False
    assert "可执行文件" in (result.reason or "")


def test_file_security_rejects_unsupported_extension() -> None:
    result = FileSecurityService().validate(
        "file.zip",
        "application/zip",
        b"PK",
    )

    assert result.allowed is False
    assert "不支持" in (result.reason or "")


def test_file_security_sanitizes_filename() -> None:
    result = FileSecurityService().validate(
        "../../report.pdf",
        "application/pdf",
        b"%PDF-1.4",
    )

    assert result.sanitized_filename == "report.pdf"


def test_file_security_rejects_uppercase_executable() -> None:
    result = FileSecurityService().validate(
        "evil.EXE",
        "application/octet-stream",
        b"MZ",
    )

    assert result.allowed is False


def test_file_security_rejects_double_extension() -> None:
    result = FileSecurityService().validate(
        "report.pdf.exe",
        "application/pdf",
        b"%PDF-1.4",
    )

    assert result.allowed is False


def test_file_security_rejects_missing_extension() -> None:
    result = FileSecurityService().validate(
        "report",
        "application/pdf",
        b"%PDF-1.4",
    )

    assert result.allowed is False
