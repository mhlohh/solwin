from ml_service.api.schemas import SecurityRiskLevel
from ml_service.security.email_analyzer import EmailAnalyzer


def test_email_extraction_from_text() -> None:
    analyzer = EmailAnalyzer()
    text = (
        "Please reach out to support@shopzilla.com or "
        "suspicious@amaz0n-security.com for assistance."
    )
    emails = analyzer.extract_emails(text)
    assert len(emails) == 2
    assert "support@shopzilla.com" in emails
    assert "suspicious@amaz0n-security.com" in emails


def test_typosquatting_brand_lookalike() -> None:
    analyzer = EmailAnalyzer()
    res = analyzer.analyze_email("service@amaz0n-security.com")
    assert res.risk_level == SecurityRiskLevel.HIGH
    assert any("typosquatting_lookalike" in r or "brand_impersonation" in r for r in res.reasons)


def test_disposable_email_domain() -> None:
    analyzer = EmailAnalyzer()
    res = analyzer.analyze_email("hacker@mailinator.com")
    assert res.is_disposable is True
    assert "disposable_temporary_email_domain" in res.reasons
    assert res.risk_level == SecurityRiskLevel.HIGH


def test_legitimate_customer_email() -> None:
    analyzer = EmailAnalyzer()
    res = analyzer.analyze_email("regular.user@gmail.com")
    assert res.is_free_provider is True
    assert res.risk_level in {SecurityRiskLevel.SAFE, SecurityRiskLevel.LOW}


def test_legitimate_configured_brands_not_flagged() -> None:
    analyzer = EmailAnalyzer()
    genuine_brand_emails = [
        "support@google.com",
        "orders@amazon.com",
        "service@paypal.com",
        "billing@microsoft.com",
        "support@apple.com",
        "info@netflix.com",
        "help@shopzilla.com",
    ]
    for email in genuine_brand_emails:
        res = analyzer.analyze_email(email)
        assert res.risk_level in {SecurityRiskLevel.SAFE, SecurityRiskLevel.LOW}, (
            f"Genuine brand email {email} was wrongly flagged as {res.risk_level} with reasons {res.reasons}"
        )
        assert not any("typosquatting" in r for r in res.reasons)


def test_actual_lookalike_variants_flagged() -> None:
    analyzer = EmailAnalyzer()
    lookalike_emails = [
        "security@g00gle.com",
        "alert@goog1e.com",
        "verify@paypa1.com",
        "service@amaz0n.com",
        "billing@micros0ft.com",
    ]
    for email in lookalike_emails:
        res = analyzer.analyze_email(email)
        assert res.risk_level == SecurityRiskLevel.HIGH
        assert any("typosquatting" in r for r in res.reasons)

