from datetime import datetime, timezone
import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ml_service.core.config import get_settings

from ml_service.analytics.frequency import FrequencyTracker
from ml_service.api.schemas import (
    ActionRecommendation,
    BatchClusterRequest,
    BatchClusterResponse,
    BatchUnifiedAnalysisRequest,
    BatchUnifiedAnalysisResponse,
    BusinessCategory,
    ClassificationResult,
    ClusterAssignment,
    ClusterMetadata,
    ComplaintInput,
    ConversationSummary,
    CustomerReviewOutput,
    CustomerReviewRequest,
    EmailAnalysis,
    EmailAnalysisRequest,
    EmailAnalysisResponse,
    FrequencyReport,
    GeminiAnalysisOutput,
    HealthResponse,
    ReadinessResponse,
    RecommendationRequest,
    ResolutionResult,
    ReviewClassification,
    ReviewClustering,
    ReviewContent,
    ReviewModelMetadata,
    ReviewOverallRisk,
    ReviewPhishing,
    ReviewProcessing,
    ReviewRecommendation,
    ReviewResolution,
    ReviewSecurity,
    ReviewSentiment,
    ReviewSocialEngineering,
    ReviewSource,
    ReviewSummary,
    ReviewUrgency,
    SecurityAnalysisSummary,
    SecurityRiskLevel,
    SentimentResult,
    SocialEngineeringResult,
    SummarizeRequest,
    UnifiedAnalysisRequest,
    UnifiedAnalysisResponse,
    UrgencyResult,
    URLAnalysis,
    URLAnalysisRequest,
    URLAnalysisResponse,
)
from ml_service.classification.classifier import ComplaintClassifier
from ml_service.clustering.clusterer import ComplaintClusterer
from ml_service.core.model_registry import ModelRegistry
from ml_service.orchestration.pipeline import GeminiPipeline
from ml_service.preprocessing.cleaner import build_complaint_text
from ml_service.recommendation.engine import RecommendationEngine
from ml_service.resolution.detector import ResolutionDetector
from ml_service.security.email_analyzer import EmailAnalyzer
from ml_service.security.url_analyzer import URLAnalyzer
from ml_service.summarization.summarizer import ConversationSummarizer
from ml_service.urgency.detector import UrgencyDetector

logger = logging.getLogger(__name__)

router = APIRouter()

# Deterministic urgency-detector signals that indicate theft / compromise /
# fraud. Used by the security-signal category guard: when these fire and the
# local fallback classifier is unconfident, the complaint is routed as
# SECURITY_CONCERN so a likely fraud report can never reach an unrelated team.
_SECURITY_SIGNAL_NAMES = frozenset(
    {
        "unauthorized_transaction_indicator",
        "stolen_credential_or_item",
        "account_compromise_detected",
        "phishing_threat_detected",
        "malware_infection_detected",
        "ransomware_detected",
        "fraud_alert",
        "card_theft",
    }
)


def _apply_security_signal_guard(
    category: BusinessCategory,
    urgency: object,
    signals: list[str],
    needs_review: bool,
) -> tuple[BusinessCategory, bool]:
    """Return (possibly overridden) category and whether the guard fired.

    Fires only when urgency is CRITICAL with a security signal and the local
    classifier flagged the text for review — i.e. the fallback path; the
    Gemini path classifies these correctly and is never touched.
    """
    urgency_val = str(getattr(urgency, "value", urgency) or "").upper()
    if (
        urgency_val == "CRITICAL"
        and needs_review
        and any(s in _SECURITY_SIGNAL_NAMES for s in signals)
    ):
        return BusinessCategory.SECURITY_CONCERN, True
    return category, False


def registry(request: Request) -> ModelRegistry:
    return request.app.state.model_registry  # type: ignore[no-any-return]


def classifier(request: Request) -> ComplaintClassifier:
    return request.app.state.classifier  # type: ignore[no-any-return]


def clusterer(request: Request) -> ComplaintClusterer:
    return request.app.state.clusterer  # type: ignore[no-any-return]


def frequency_tracker(request: Request) -> FrequencyTracker:
    return request.app.state.frequency_tracker  # type: ignore[no-any-return]


def urgency_detector(request: Request) -> UrgencyDetector:
    return request.app.state.urgency_detector  # type: ignore[no-any-return]


def resolution_detector(request: Request) -> ResolutionDetector:
    return request.app.state.resolution_detector  # type: ignore[no-any-return]


def recommendation_engine(request: Request) -> RecommendationEngine:
    return request.app.state.recommendation_engine  # type: ignore[no-any-return]


def url_analyzer(request: Request) -> URLAnalyzer:
    return request.app.state.url_analyzer  # type: ignore[no-any-return]


def email_analyzer(request: Request) -> EmailAnalyzer:
    return request.app.state.email_analyzer  # type: ignore[no-any-return]


def summarizer(request: Request) -> ConversationSummarizer:
    return request.app.state.summarizer  # type: ignore[no-any-return]


def gemini_pipeline(request: Request) -> GeminiPipeline:
    return request.app.state.gemini_pipeline  # type: ignore[no-any-return]


@router.get("/health", response_model=HealthResponse, tags=["operations"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="customer-complaint-intelligence", version="0.1.0")


@router.get("/ready", response_model=ReadinessResponse, tags=["operations"])
def ready(request: Request) -> ReadinessResponse | JSONResponse:
    if registry(request).is_ready() and classifier(request).is_loaded:
        return ReadinessResponse(status="ready", models_ready=True)
    result = ReadinessResponse(
        status="not_ready",
        models_ready=False,
        detail="No production model is registered and loaded. "
        "Train and register a model before serving.",
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=result.model_dump(),
    )


@router.get("/api/v1/models", tags=["models"])
def list_models(request: Request) -> dict[str, object]:
    return {"models": registry(request).list()}


@router.post("/api/v1/classify", response_model=ClassificationResult, tags=["classification"])
def classify_complaint(
    complaint: ComplaintInput,
    request: Request,
    threshold: float | None = None,
) -> ClassificationResult:
    clf = classifier(request)
    if not clf.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Classifier model is not ready.",
        )
    result = clf.classify(message=complaint.message, subject=complaint.subject, threshold=threshold)

    # Accumulate live production telemetry
    tracker = frequency_tracker(request)
    tracker.record_event(category=result.category.value)

    return result


@router.post("/api/v1/cluster", response_model=ClusterAssignment, tags=["clustering"])
def cluster_single(
    complaint: ComplaintInput,
    request: Request,
) -> ClusterAssignment:
    cl = clusterer(request)
    if not cl.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clusterer model is not ready.",
        )
    assignment = cl.assign(message=complaint.message, subject=complaint.subject)
    # Record cluster in live telemetry
    tracker = frequency_tracker(request)
    tracker.record_event(
        category=assignment.dominant_category.value,
        cluster_id=assignment.cluster_id,
    )
    return assignment


@router.post("/api/v1/cluster/batch", response_model=BatchClusterResponse, tags=["clustering"])
def cluster_batch(
    batch: BatchClusterRequest,
    request: Request,
) -> BatchClusterResponse:
    cl = clusterer(request)
    if not cl.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clusterer model is not ready.",
        )
    pairs = [(c.message, c.subject) for c in batch.complaints]
    assignments = cl.assign_batch(pairs)
    tracker = frequency_tracker(request)
    for a in assignments:
        tracker.record_event(category=a.dominant_category.value, cluster_id=a.cluster_id)
    return BatchClusterResponse(assignments=assignments, total_processed=len(assignments))


@router.get("/api/v1/clusters", response_model=list[ClusterMetadata], tags=["clustering"])
def get_clusters(request: Request) -> list[ClusterMetadata]:
    cl = clusterer(request)
    if not cl.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clusterer model is not ready.",
        )
    return cl.list_clusters()


@router.get("/api/v1/analytics/frequency", response_model=FrequencyReport, tags=["analytics"])
def get_frequency_analytics(request: Request) -> FrequencyReport:
    tracker = frequency_tracker(request)
    return tracker.get_report()


@router.post("/api/v1/urgency", response_model=UrgencyResult, tags=["urgency"])
def detect_urgency(
    complaint: ComplaintInput,
    request: Request,
) -> UrgencyResult:
    detector = urgency_detector(request)
    return detector.detect(message=complaint.message, subject=complaint.subject)


@router.post("/api/v1/resolution", response_model=ResolutionResult, tags=["resolution"])
def detect_resolution(
    complaint: ComplaintInput,
    request: Request,
) -> ResolutionResult:
    detector = resolution_detector(request)
    return detector.detect(message=complaint.message, subject=complaint.subject)


@router.post("/api/v1/recommend", response_model=ActionRecommendation, tags=["recommendation"])
def recommend_action(
    req: RecommendationRequest,
    request: Request,
) -> ActionRecommendation:
    engine = recommendation_engine(request)

    # Derive urgency first, then category — the security-signal guard needs
    # the urgency signals to protect against an unconfident fallback
    # prediction routing a likely fraud/compromise report to the wrong team.
    urgency = req.urgency
    urgency_signals: list[str] = []
    if urgency is None:
        urg_detector = urgency_detector(request)
        urg_res = urg_detector.detect(message=req.complaint.message, subject=req.complaint.subject)
        urgency = urg_res.urgency
        urgency_signals = urg_res.signals

    category = req.category
    if category is None:
        clf = classifier(request)
        if clf.is_loaded:
            cat_res = clf.classify(message=req.complaint.message, subject=req.complaint.subject)
            category, _ = _apply_security_signal_guard(
                cat_res.category, urgency, urgency_signals, cat_res.needs_review
            )

    resolution = req.resolution
    if resolution is None:
        res_detector = resolution_detector(request)
        res_res = res_detector.detect(message=req.complaint.message, subject=req.complaint.subject)
        resolution = res_res.status

    return engine.recommend(
        category=category,
        urgency=urgency,
        resolution=resolution,
        security_risk=req.security_risk,
    )


@router.post("/api/v1/url/analyze", response_model=URLAnalysisResponse, tags=["security"])
def analyze_urls(
    req: URLAnalysisRequest,
    request: Request,
) -> URLAnalysisResponse:
    analyzer = url_analyzer(request)
    results: list[URLAnalysis] = []
    if req.url:
        results.append(analyzer.analyze_url(req.url))
    if req.text:
        text_results = analyzer.analyze_text(req.text)
        # Avoid duplicate if same url was explicitly passed
        existing_urls = {r.url for r in results}
        for tr in text_results:
            if tr.url not in existing_urls:
                results.append(tr)
                existing_urls.add(tr.url)

    return URLAnalysisResponse(results=results, total_found=len(results))


@router.post("/api/v1/email/analyze", response_model=EmailAnalysisResponse, tags=["security"])
def analyze_emails(
    req: EmailAnalysisRequest,
    request: Request,
) -> EmailAnalysisResponse:
    analyzer = email_analyzer(request)
    results: list[EmailAnalysis] = []
    if req.email:
        results.append(analyzer.analyze_email(req.email))
    if req.text:
        text_results = analyzer.analyze_text(req.text)
        existing_emails = {r.email for r in results}
        for tr in text_results:
            if tr.email not in existing_emails:
                results.append(tr)
                existing_emails.add(tr.email)

    return EmailAnalysisResponse(results=results, total_found=len(results))


@router.post(
    "/api/v1/summarize",
    response_model=ConversationSummary,
    tags=["summarization"],
)
def summarize_conversation(
    req: SummarizeRequest,
    request: Request,
) -> ConversationSummary:
    engine = summarizer(request)

    # Gemini is the PRIMARY summarizer: when the caller opts in, run the one
    # structured Gemini call and hand its summary text to the summarizer.
    # Any provider failure degrades to the extractive summarizer.
    gemini_output: GeminiAnalysisOutput | None = None
    if req.prefer_llm:
        provider = getattr(request.app.state, "ai_provider", None)
        settings = get_settings()
        if provider is not None and provider.is_available and settings.gemini_enabled:
            try:
                gemini_output = provider.analyze(req.complaint.subject, req.complaint.message)
            except Exception as exc:  # typed provider errors — degrade quietly
                logger.warning("Summarize: Gemini unavailable (%s), using extractive", type(exc).__name__)

    return engine.summarize(
        message=req.complaint.message,
        subject=req.complaint.subject,
        prefer_llm=req.prefer_llm,
        gemini_output=gemini_output,
    )


@router.post(
    "/api/v1/analyze",
    response_model=UnifiedAnalysisResponse,
    tags=["unified"],
)
def analyze_complaint(
    req: UnifiedAnalysisRequest,
    request: Request,
) -> UnifiedAnalysisResponse:
    start_time = time.perf_counter()
    warnings: list[str] = []

    msg = req.complaint.message
    subj = req.complaint.subject
    text = build_complaint_text(msg, subj)
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint must include at least one non-empty 'message' or 'subject' field.",
        )

    # 0. Local security analysis runs FIRST — before any Gemini call
    #    (URL/email analyzers must never be bypassed by hosted AI)
    security_summary: SecurityAnalysisSummary | None = None
    if req.include_security:
        try:
            u_analyzer = url_analyzer(request)
            e_analyzer = email_analyzer(request)
            urls = u_analyzer.analyze_text(text)
            emails = e_analyzer.analyze_text(text)

            all_risks = [u.risk_level for u in urls] + [em.risk_level for em in emails]
            if SecurityRiskLevel.HIGH in all_risks:
                agg_risk = SecurityRiskLevel.HIGH
            elif SecurityRiskLevel.MEDIUM in all_risks:
                agg_risk = SecurityRiskLevel.MEDIUM
            elif SecurityRiskLevel.LOW in all_risks:
                agg_risk = SecurityRiskLevel.LOW
            elif SecurityRiskLevel.SAFE in all_risks:
                agg_risk = SecurityRiskLevel.SAFE
            else:
                agg_risk = SecurityRiskLevel.SAFE

            reasons: list[str] = []
            for u in urls:
                reasons.extend(u.signals)
            for em in emails:
                reasons.extend(em.reasons)

            security_summary = SecurityAnalysisSummary(
                urls=urls,
                emails=emails,
                aggregate_risk=agg_risk,
                requires_quarantine=agg_risk == SecurityRiskLevel.HIGH,
                risk_reasons=list(dict.fromkeys(reasons)),
            )
        except Exception as e:
            warnings.append(f"Security analysis failed: {e}")

    # 1. Tiered pipeline — local ML/NLP primary (classification, sentiment,
    #    social engineering), Gemini secondary (summary + cross-check).
    pipeline = gemini_pipeline(request)
    pipeline_result = pipeline.run(subj, msg)
    warnings.extend(pipeline_result.warnings)

    classification_result = pipeline_result.classification

    # Track model provenance for response
    model_versions: dict[str, str] = {
        "classification": pipeline_result.model_name,
        "sentiment": "local-nlp-lexicon-v1",
        "social_engineering": "local-rule-engine-v1",
        "summary": "pending",
    }

    # 2. Clustering
    cluster_res: ClusterAssignment | None = None
    if req.include_cluster:
        try:
            cl_engine = clusterer(request)
            if cl_engine.is_loaded:
                cluster_res = cl_engine.assign(msg, subj)
            else:
                warnings.append("Clusterer model is not loaded.")
        except Exception as e:
            warnings.append(f"Clustering failed: {e}")

    # 4. Urgency Detection (always local) — computed before frequency tracking
    #    so the security-signal category guard below can run first.
    urgency_res: UrgencyResult | None = None
    if req.include_urgency:
        try:
            urg_engine = urgency_detector(request)
            urgency_res = urg_engine.detect(msg, subj)
        except Exception as e:
            warnings.append(f"Urgency detection failed: {e}")

    # 4.5 Security-signal category guard (primary local tier).
    # When the deterministic urgency detector fires CRITICAL security signals
    # and the local classifier is unconfident (needs_review), route the
    # complaint as SECURITY_CONCERN so the recommendation engine can never
    # send a likely fraud/compromise report to an unrelated team.
    if urgency_res is not None:
        guarded_cat, fired = _apply_security_signal_guard(
            classification_result.category,
            urgency_res.urgency,
            urgency_res.signals,
            classification_result.needs_review,
        )
        if fired:
            classification_result = ClassificationResult(
                category=guarded_cat,
                confidence=classification_result.confidence,
                probabilities=classification_result.probabilities,
                needs_review=True,
                model_name=classification_result.model_name,
                model_version=classification_result.model_version,
                fine_grained_intent=classification_result.fine_grained_intent,
            )
            warnings.append("security_signal_category_guard")

    # 3. Frequency tracking (after the guard so telemetry reflects the final category)
    try:
        freq_tracker = frequency_tracker(request)
        freq_tracker.record_event(
            category=classification_result.category.value,
            cluster_id=cluster_res.cluster_id if cluster_res else None,
        )
    except Exception as e:
        warnings.append(f"Frequency tracking failed: {e}")

    # 5. Resolution Status Detection (always local)
    resolution_res: ResolutionResult | None = None
    if req.include_resolution:
        try:
            res_engine = resolution_detector(request)
            resolution_res = res_engine.detect(msg, subj)
        except Exception as e:
            warnings.append(f"Resolution detection failed: {e}")

    # 6. Action Recommendation (always local deterministic rules)
    recommendation_res: ActionRecommendation | None = None
    if req.include_recommendation:
        try:
            rec_engine = recommendation_engine(request)
            recommendation_res = rec_engine.recommend(
                category=classification_result.category,
                urgency=urgency_res.urgency if urgency_res else None,
                resolution=resolution_res.status if resolution_res else None,
                security_risk=(
                    security_summary.aggregate_risk.value if security_summary else None
                ),
            )
        except Exception as e:
            warnings.append(f"Recommendation failed: {e}")

    # 7. Conversation Summary (Gemini text if available, else extractive)
    summary_res: ConversationSummary | None = None
    if req.include_summary:
        try:
            sum_engine = summarizer(request)
            # Pass Gemini output so summarizer can use pre-computed summary_text
            # without making a second API call.
            if pipeline_result.summary_text:
                gemini_output_for_summary = type(
                    "_G", (), {"summary_text": pipeline_result.summary_text}
                )()
                summary_res = sum_engine.summarize(
                    message=msg,
                    subject=subj,
                    prefer_llm=True,
                    gemini_output=gemini_output_for_summary,
                )
                model_versions["summary"] = get_settings().gemini_model
            else:
                summary_res = sum_engine.summarize(
                    message=msg,
                    subject=subj,
                    prefer_llm=req.prefer_llm,
                )
                model_versions["summary"] = "extractive"
        except Exception as e:
            warnings.append(f"Summarization failed: {e}")
            model_versions["summary"] = "failed"

    # 8. Sentiment (from pipeline result)
    sentiment_res: SentimentResult | None = None
    if req.include_sentiment:
        sentiment_res = pipeline_result.sentiment

    # 9. Social engineering (from pipeline result)
    se_res: SocialEngineeringResult | None = None
    if req.include_security:
        se_res = pipeline_result.social_engineering

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return UnifiedAnalysisResponse(
        complaint_id=req.complaint_id,
        classification=classification_result,
        cluster=cluster_res,
        urgency=urgency_res,
        resolution=resolution_res,
        recommendation=recommendation_res,
        security=security_summary,
        summary=summary_res,
        sentiment=sentiment_res,
        social_engineering=se_res,
        model_versions=model_versions,
        processing_time_ms=latency_ms,
        warnings=warnings,
    )


@router.post(
    "/api/v1/analyze/batch",
    response_model=BatchUnifiedAnalysisResponse,
    tags=["orchestration"],
)
def analyze_batch(
    batch: BatchUnifiedAnalysisRequest,
    request: Request,
) -> BatchUnifiedAnalysisResponse:
    start_time = time.perf_counter()
    results: list[UnifiedAnalysisResponse] = []
    for item in batch.items:
        res = analyze_complaint(req=item, request=request)
        results.append(res)
    total_time = round((time.perf_counter() - start_time) * 1000, 2)
    return BatchUnifiedAnalysisResponse(
        results=results,
        total_processed=len(results),
        processing_time_ms=total_time,
    )


@router.post(
    "/api/v1/analyze/review",
    response_model=CustomerReviewOutput,
    tags=["orchestration"],
)
def analyze_review(
    req: CustomerReviewRequest,
    request: Request,
) -> CustomerReviewOutput:
    """Analyze customer review and format output strictly adhering to CustomerReviewOutput schema."""
    start_time = time.perf_counter()
    review_id = req.review_id or f"REV-{uuid.uuid4().hex[:6].upper()}"

    # Delegate to unified analysis pipeline
    unified_req = UnifiedAnalysisRequest(
        complaint=ComplaintInput(
            message=req.message,
            subject=req.subject,
        ),
        complaint_id=review_id,
        include_cluster=req.include_cluster,
        include_urgency=req.include_urgency,
        include_resolution=req.include_resolution,
        include_recommendation=req.include_recommendation,
        include_security=req.include_security,
        include_summary=req.include_summary,
        include_sentiment=req.include_sentiment,
        prefer_llm=req.prefer_llm,
    )
    unified_res = analyze_complaint(req=unified_req, request=request)

    # 1. Source
    source = ReviewSource(
        source_type=req.source_type,
        source_record_id=req.source_record_id,
        domain=req.domain,
        channel=req.channel,
    )

    # 2. Content
    content = ReviewContent(
        subject=req.subject,
        message=req.message,
    )

    # 3. Classification
    classification = ReviewClassification(
        category=unified_res.classification.category.value,
        fine_grained_intent=unified_res.classification.fine_grained_intent,
        confidence=round(unified_res.classification.confidence, 4),
        needs_review=unified_res.classification.needs_review,
    )

    # 4. Sentiment
    sentiment_label = unified_res.sentiment.label.value if unified_res.sentiment else "NEUTRAL"
    sentiment_score = unified_res.sentiment.score if unified_res.sentiment else 0.5
    sentiment = ReviewSentiment(
        label=sentiment_label,
        score=round(sentiment_score, 4),
    )

    # 5. Keywords
    keywords: list[str] = []
    if unified_res.summary and unified_res.summary.key_phrases:
        keywords = unified_res.summary.key_phrases
    elif unified_res.resolution and unified_res.resolution.signals:
        keywords = unified_res.resolution.signals[:5]

    # 6. Summary
    if unified_res.summary and unified_res.summary.customer_issue:
        summary_text = unified_res.summary.customer_issue
    else:
        summary_text = req.subject or req.message[:120]
    summary = ReviewSummary(text=summary_text)

    # 7. Clustering
    sim_score = (
        round(max(0.0, min(1.0, 1.0 - unified_res.cluster.distance)), 4)
        if unified_res.cluster
        else 0.5
    )
    clustering = ReviewClustering(
        cluster_id=str(unified_res.cluster.cluster_id) if unified_res.cluster else "cluster_unknown",
        cluster_name=unified_res.cluster.cluster_name if unified_res.cluster else "General Inquiries",
        similarity_score=sim_score,
    )

    # 8. Urgency
    urgency_level = unified_res.urgency.urgency.value if unified_res.urgency else "MEDIUM"
    urgency_score = unified_res.urgency.confidence if unified_res.urgency else 0.5
    urgency_reasons = (
        unified_res.urgency.reasons or unified_res.urgency.signals
        if unified_res.urgency
        else []
    )
    urgency = ReviewUrgency(
        level=urgency_level,
        score=round(urgency_score, 4),
        reasons=urgency_reasons,
    )

    # 9. Resolution
    resolution_status = unified_res.resolution.status.value if unified_res.resolution else "UNRESOLVED"
    resolution_conf = unified_res.resolution.confidence if unified_res.resolution else 0.5
    resolution_ev = unified_res.resolution.signals if unified_res.resolution else []
    resolution = ReviewResolution(
        status=resolution_status,
        confidence=round(resolution_conf, 4),
        evidence=resolution_ev,
    )

    # 10. Security
    urls_data = [u.model_dump() for u in unified_res.security.urls] if unified_res.security else []
    emails_data = [e.model_dump() for e in unified_res.security.emails] if unified_res.security else []
    sec_risk_level = (
        unified_res.security.aggregate_risk.value
        if unified_res.security and unified_res.security.aggregate_risk
        else "SAFE"
    )
    # Numerical risk score mapped from risk level
    risk_score_map = {"SAFE": 0.0, "LOW": 0.25, "MEDIUM": 0.65, "HIGH": 0.95}
    sec_risk_score = risk_score_map.get(sec_risk_level.upper(), 0.1)

    phishing_detected = any(u.get("risk_level") in ("HIGH", "MEDIUM") for u in urls_data)
    phishing_conf = 0.9 if phishing_detected else 0.0

    se_detected = bool(unified_res.social_engineering and unified_res.social_engineering.detected)
    se_techniques = unified_res.social_engineering.techniques if unified_res.social_engineering else []

    security = ReviewSecurity(
        risk_level=sec_risk_level,
        risk_score=sec_risk_score,
        phishing=ReviewPhishing(detected=phishing_detected, confidence=phishing_conf),
        urls=urls_data,
        email_addresses=emails_data,
        social_engineering=ReviewSocialEngineering(detected=se_detected, techniques=se_techniques),
        reasons=unified_res.security.risk_reasons if unified_res.security else [],
    )

    # 11. Overall Risk
    # Combine urgency severity and security risk — take the max so a
    # high-severity input always dominates the aggregate instead of being
    # averaged away (urgency.score is detection confidence, not severity).
    urgency_severity_map = {"CRITICAL": 1.0, "HIGH": 0.75, "MEDIUM": 0.45, "LOW": 0.2}
    urgency_severity = urgency_severity_map.get(urgency_level.upper(), 0.2)
    overall_score = round(max(urgency_severity, sec_risk_score), 4)
    if overall_score >= 0.8:
        overall_level = "CRITICAL" if sec_risk_score >= 0.9 or urgency_severity >= 1.0 else "HIGH"
    elif overall_score >= 0.5:
        overall_level = "MEDIUM"
    elif overall_score >= 0.25:
        overall_level = "LOW"
    else:
        overall_level = "SAFE"

    factors: list[str] = []
    if urgency_reasons:
        factors.extend([f"Urgency: {r}" for r in urgency_reasons[:2]])
    if security.reasons:
        factors.extend([f"Security: {r}" for r in security.reasons[:2]])
    if not factors:
        factors = ["Standard inquiry"]

    overall_risk = ReviewOverallRisk(
        level=overall_level,
        score=overall_score,
        factors=factors,
    )

    # 12. Recommendation
    if unified_res.recommendation:
        rec = ReviewRecommendation(
            primary_action=unified_res.recommendation.primary_action.value,
            priority="HIGH" if urgency_level in ("CRITICAL", "HIGH") else "NORMAL",
            secondary_actions=[s.value for s in unified_res.recommendation.secondary_actions],
            rationale=unified_res.recommendation.rationale,
        )
    else:
        rec = ReviewRecommendation(
            primary_action="STANDARD_SUPPORT_RESPONSE",
            priority="NORMAL",
            secondary_actions=[],
            rationale="Standard complaint triage",
        )

    # 13. Model Metadata
    model_metadata = ReviewModelMetadata(
        classifier=unified_res.model_versions.get("classification", "complaint_classifier_v1"),
        intent_classifier="intent_classifier_v1",
        clusterer="clusterer_v1",
        sentiment_model=unified_res.model_versions.get("sentiment", "local-nlp-lexicon-v1"),
        summarizer=unified_res.model_versions.get("summary", "extractive_v1"),
    )

    # 14. Processing
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    processing = ReviewProcessing(
        processed_at=datetime.now(timezone.utc).isoformat(),
        processing_time_ms=latency_ms,
        warnings=unified_res.warnings,
    )

    return CustomerReviewOutput(
        review_id=review_id,
        source=source,
        content=content,
        classification=classification,
        sentiment=sentiment,
        keywords=keywords,
        summary=summary,
        clustering=clustering,
        urgency=urgency,
        resolution=resolution,
        security=security,
        overall_risk=overall_risk,
        recommendation=rec,
        model_metadata=model_metadata,
        processing=processing,
    )


@router.get("/api/v1/capabilities", tags=["operations"])
def capabilities() -> dict[str, object]:
    return {
        "status": "active",
        "available": [
            "health",
            "readiness",
            "model_registry",
            "classification",
            "clustering",
            "frequency_analytics",
            "urgency",
            "resolution",
            "recommendation",
            "url",
            "email",
            "summary",
            "unified_analysis",
        ],
        "planned": [],
    }
