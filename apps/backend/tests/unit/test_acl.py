from datetime import datetime, timezone

from stock_research.retrieval.acl import AccessContext, AclFilter, DocumentAccess
from stock_research.retrieval.golden import GoldenQuery, RetrievalEvaluator


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


def test_cross_tenant_recall_is_zero_after_acl_filter() -> None:
    context = AccessContext(
        tenant_id="tenant-1",
        user_id="user-1",
        allowed_visibility=frozenset({"PUBLIC", "PRIVATE"}),
        allowed_licenses=frozenset(),
        allowed_symbols=frozenset(),
    )
    documents = [
        DocumentAccess("doc-1", "tenant-1", "user-1", "PUBLIC", None, None, None),
        DocumentAccess("doc-2", "tenant-1", "user-1", "PRIVATE", None, None, None),
        DocumentAccess("cross-tenant", "tenant-2", "user-2", "PUBLIC", None, None, None),
    ]

    allowed = AclFilter().filter(documents, context)
    allowed_ids = frozenset(doc.doc_id for doc in allowed)
    assert "cross-tenant" not in allowed_ids

    # 检索结果经过 ACL 过滤后，不得包含任何跨租户文档。
    ranked = ["doc-1", "cross-tenant", "doc-2"]
    filtered_ranked = [doc_id for doc_id in ranked if doc_id in allowed_ids]
    assert "cross-tenant" not in filtered_ranked

    result = RetrievalEvaluator().evaluate(
        queries=[GoldenQuery("q", frozenset({"doc-1"}))],
        ranked_lists={"q": filtered_ranked},
        allowed_doc_ids=allowed_ids,
    )
    assert result.acl_leakage == 0
