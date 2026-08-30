from stock_research.skills.intent_router import IntentRouter


def test_intent_router_routes_research_by_default() -> None:
    assert IntentRouter().route("分析一下这只股票") == IntentRouter().route("分析一下这只股票")
    assert IntentRouter().route("分析一下这只股票").intent == "research"


def test_intent_router_routes_document_report_review() -> None:
    router = IntentRouter()

    assert router.route("上传文档").intent == "document"
    assert router.route("生成报告").intent == "report"
    assert router.route("请审核").intent == "review"
