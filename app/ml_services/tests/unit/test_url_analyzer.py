from ml_service.api.schemas import SecurityRiskLevel
from ml_service.security.url_analyzer import URLAnalyzer


def test_url_extraction_from_text() -> None:
    analyzer = URLAnalyzer()
    text = (
        "Please verify your account here: https://secure-login.xyz/auth "
        "and also see www.example.com/test."
    )
    urls = analyzer.extract_urls(text)
    assert len(urls) == 2
    assert "https://secure-login.xyz/auth" in urls
    assert "www.example.com/test" in urls


def test_ip_address_host_risk() -> None:
    analyzer = URLAnalyzer()
    res = analyzer.analyze_url("http://192.168.1.100/login/password.php")
    assert res.domain == "192.168.1.100"
    assert "ip_address_host" in res.signals
    assert res.risk_level in {SecurityRiskLevel.HIGH, SecurityRiskLevel.MEDIUM}
    assert res.risk_score >= 0.40


def test_punycode_homograph_domain() -> None:
    analyzer = URLAnalyzer()
    res = analyzer.analyze_url("http://xn--amazn-7qa.com/account")
    assert "punycode_homograph_domain" in res.signals
    assert res.risk_score >= 0.40


def test_url_shortener_risk() -> None:
    analyzer = URLAnalyzer()
    res_bitly = analyzer.analyze_url("https://bit.ly/3xYqzP")
    assert "url_shortener" in res_bitly.signals
    assert res_bitly.risk_level in {SecurityRiskLevel.MEDIUM, SecurityRiskLevel.HIGH}

    res_tinyurl = analyzer.analyze_url("https://tinyurl.com/xyz123")
    assert "url_shortener" in res_tinyurl.signals
    assert res_tinyurl.risk_level in {SecurityRiskLevel.MEDIUM, SecurityRiskLevel.HIGH}


def test_suspicious_shortened_url() -> None:
    analyzer = URLAnalyzer()
    # Shortened URL with suspicious login keyword in path/query
    res = analyzer.analyze_url("https://bit.ly/login-verification")
    assert "url_shortener" in res.signals
    assert any("suspicious_path_keywords" in s for s in res.signals)
    assert res.risk_level == SecurityRiskLevel.HIGH


def test_configurable_shortener_min_risk() -> None:
    analyzer_low = URLAnalyzer(shortener_score_penalty=0.10, shortener_min_risk=SecurityRiskLevel.LOW)
    res_low = analyzer_low.analyze_url("https://bit.ly/safe")
    assert res_low.risk_level == SecurityRiskLevel.LOW


def test_legitimate_https_url() -> None:
    analyzer = URLAnalyzer()
    res = analyzer.analyze_url("https://shopzilla.com/help")
    assert res.risk_level == SecurityRiskLevel.SAFE
    assert res.risk_score < 0.20
