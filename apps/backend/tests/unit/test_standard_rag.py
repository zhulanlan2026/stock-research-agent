from stock_research.retrieval.standard_rag import (
    StandardRagEvidence,
    StandardRagService,
)


def test_standard_rag_retrieves_bm25_evidence() -> None:
    service = StandardRagService(
        [
            StandardRagEvidence("e1", "贵州茅台 供应商 合同"),
            StandardRagEvidence("e2", "银行 利率 风险"),
        ]
    )

    assert service.retrieve("贵州茅台 供应商") == ["e1"]
    assert service.retrieve("银行 利率") == ["e2"]
