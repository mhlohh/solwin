from ml_service.api.schemas import ResolutionStatus
from ml_service.summarization.summarizer import ConversationSummarizer


def test_summarizer_empty_input() -> None:
    summarizer = ConversationSummarizer()
    res = summarizer.summarize(message=None, subject=None)
    assert res.resolution_status == ResolutionStatus.UNKNOWN
    assert res.customer_issue == "No message content provided."
    assert res.actions_taken == []
    assert res.pending_actions == []
    assert res.entities_extracted == {}
    assert res.summary_mode == "extractive"


def test_summarizer_extracts_entities() -> None:
    summarizer = ConversationSummarizer()
    text = (
        "I placed order #AB12345 on 2026-03-12 for $149.99. "
        "My contact email is customer@domain.com and phone is +1-555-123-4567. "
        "The item never arrived."
    )
    summary = summarizer.summarize(message=text, subject="Order missing")
    entities = summary.entities_extracted

    assert "AB12345" in entities.get("order_ids", [])
    assert any("$149.99" in amt for amt in entities.get("monetary_amounts", []))
    assert any("2026-03-12" in d for d in entities.get("dates", []))
    assert "customer@domain.com" in entities.get("emails", [])
    assert any("555" in p for p in entities.get("phone_numbers", []))


def test_summarizer_detects_actions_and_pending() -> None:
    summarizer = ConversationSummarizer()
    text = (
        "I already contacted support two days ago and returned the item. "
        "I am still waiting for refund. Please investigate my order #12345 immediately."
    )
    summary = summarizer.summarize(message=text, subject="Return status")

    assert "Contacted support team" in summary.actions_taken
    assert "Customer returned item" in summary.actions_taken
    assert "Awaiting status update/response" in summary.pending_actions
    assert "Investigation/resolution required" in summary.pending_actions
    assert summary.resolution_status == ResolutionStatus.UNRESOLVED


def test_summarizer_prefer_llm_fallback() -> None:
    summarizer = ConversationSummarizer()
    # When no LLM is configured, gracefully fall back to extractive
    summary = summarizer.summarize(
        message="I bought shoes for $80 and they are damaged. Please refund.",
        subject="Damaged shoes",
        prefer_llm=True,
    )
    assert summary.summary_mode in ("extractive", "llm")
    assert "Damaged shoes" in summary.customer_issue or "shoes" in summary.customer_issue
