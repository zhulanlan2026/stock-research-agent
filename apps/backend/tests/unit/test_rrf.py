from stock_research.retrieval.rrf import ReciprocalRankFusion


def test_rrf_fuses_multiple_ranked_lists() -> None:
    result = ReciprocalRankFusion().fuse(
        [
            ["a", "b"],
            ["b", "c"],
        ],
        k=60,
    )

    assert result[0][0] == "b"
    assert result[0][1] > result[1][1]


def test_rrf_handles_empty_lists() -> None:
    assert ReciprocalRankFusion().fuse([]) == []


def test_rrf_is_deterministic() -> None:
    first = ReciprocalRankFusion().fuse([["a", "b"], ["b", "a"]])
    second = ReciprocalRankFusion().fuse([["a", "b"], ["b", "a"]])

    assert first == second
