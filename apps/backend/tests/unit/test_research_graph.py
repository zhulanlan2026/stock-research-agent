from stock_research.agents.research_graph import LinearResearchGraph, ResearchGraphState


async def test_linear_research_graph_runs_stages() -> None:
    state: ResearchGraphState = {
        "task_id": "task-1",
        "current_stage": "START",
        "results": {},
    }

    result = await LinearResearchGraph().run(
        state,
        [
            ("intent", lambda _state: "research"),
            ("research", lambda _state: "done"),
        ],
    )

    assert result["current_stage"] == "research"
    assert result["results"] == {"intent": "research", "research": "done"}
