from datetime import datetime, timezone

from stock_research.retrieval.acl import AccessContext, AclFilter, DocumentAccess


def test_acl_filter_allows_explicit_matches() -> None:
    context = AccessContext(
        tenant_id="tenant-1",
        user_id="user-1",
        allowed_visibility=frozenset({"PUBLIC"}),
        allowed_licenses=frozenset({"license-1"}),
        allowed_symbols=frozenset({"600519.SH"}),
    )
    document = DocumentAccess(
        doc_id="doc-1",
        tenant_id="tenant-1",
        owner_id="user-1",
        visibility_scope="PUBLIC",
        license_policy_id="license-1",
        symbol="600519.SH",
        available_at=None,
    )

    assert AclFilter().filter([document], context) == [document]


def test_acl_filter_denies_cross_tenant_and_private() -> None:
    context = AccessContext(
        tenant_id="tenant-1",
        user_id="user-1",
        allowed_visibility=frozenset({"PUBLIC"}),
        allowed_licenses=frozenset(),
        allowed_symbols=frozenset(),
    )
    documents = [
        DocumentAccess(
            doc_id="cross-tenant",
            tenant_id="tenant-2",
            owner_id="user-1",
            visibility_scope="PUBLIC",
            license_policy_id=None,
            symbol=None,
            available_at=None,
        ),
        DocumentAccess(
            doc_id="private",
            tenant_id="tenant-1",
            owner_id="user-1",
            visibility_scope="PRIVATE",
            license_policy_id=None,
            symbol=None,
            available_at=None,
        ),
    ]

    assert AclFilter().filter(documents, context) == []


def test_acl_filter_respects_available_at() -> None:
    context = AccessContext(
        tenant_id="tenant-1",
        user_id="user-1",
        allowed_visibility=frozenset({"PUBLIC"}),
        allowed_licenses=frozenset(),
        allowed_symbols=frozenset(),
    )
    document = DocumentAccess(
        doc_id="doc-1",
        tenant_id="tenant-1",
        owner_id="user-1",
        visibility_scope="PUBLIC",
        license_policy_id=None,
        symbol=None,
        available_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert AclFilter().filter(
        [document],
        context,
        as_of=datetime(2025, 12, 31, tzinfo=timezone.utc),
    ) == []
