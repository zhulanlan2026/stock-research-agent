from stock_research.agents.document_agent import DocumentAgent


async def test_document_agent_chunks_text() -> None:
    result = await DocumentAgent().run("0123456789" * 20)

    assert result.agent == "document"
    assert result.chunks
