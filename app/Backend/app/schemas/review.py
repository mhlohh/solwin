from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ReviewSource(BaseModel):
    source_type: str = "KAGGLE"
    source_record_id: str = ""
    domain: str = "E-commerce/Retail"
    channel: str = "Email"


class ReviewContent(BaseModel):
    subject: str = ""
    message: str = ""


class ReviewClassification(BaseModel):
    category: str
    fine_grained_intent: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool = False


class ReviewSentiment(BaseModel):
    label: str
    score: float = Field(ge=0.0, le=1.0)


class ReviewSummary(BaseModel):
    text: str


class ReviewClustering(BaseModel):
    cluster_id: str
    cluster_name: str
    similarity_score: float = Field(ge=0.0, le=1.0)


class ReviewUrgency(BaseModel):
    level: str
    score: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)


class ReviewResolution(BaseModel):
    status: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)


class ReviewPhishing(BaseModel):
    detected: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ReviewSocialEngineering(BaseModel):
    detected: bool = False
    techniques: List[str] = Field(default_factory=list)


class ReviewSecurity(BaseModel):
    risk_level: str = "LOW"
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    phishing: ReviewPhishing = Field(default_factory=ReviewPhishing)
    urls: List[dict] = Field(default_factory=list)
    email_addresses: List[dict] = Field(default_factory=list)
    social_engineering: ReviewSocialEngineering = Field(
        default_factory=ReviewSocialEngineering
    )
    reasons: List[str] = Field(default_factory=list)


class ReviewOverallRisk(BaseModel):
    level: str
    score: float = Field(ge=0.0, le=1.0)
    factors: List[str] = Field(default_factory=list)


class ReviewRecommendation(BaseModel):
    primary_action: str
    priority: str
    secondary_actions: List[str] = Field(default_factory=list)
    rationale: str


class ReviewModelMetadata(BaseModel):
    classifier: str = "complaint_classifier_v1"
    intent_classifier: str = "intent_classifier_v1"
    clusterer: str = "clusterer_v1"
    sentiment_model: str = "gemini"
    summarizer: str = "extractive_v1"


class ReviewProcessing(BaseModel):
    processed_at: str
    processing_time_ms: float
    warnings: List[str] = Field(default_factory=list)


class CustomerReviewOutput(BaseModel):
    review_id: str
    source: ReviewSource
    content: ReviewContent
    classification: ReviewClassification
    sentiment: ReviewSentiment
    keywords: List[str] = Field(default_factory=list)
    summary: ReviewSummary
    clustering: ReviewClustering
    urgency: ReviewUrgency
    resolution: ReviewResolution
    security: ReviewSecurity
    overall_risk: ReviewOverallRisk
    recommendation: ReviewRecommendation
    model_metadata: ReviewModelMetadata
    processing: ReviewProcessing


class CustomerReviewCreateRequest(BaseModel):
    review_id: Optional[str] = None
    source_type: str = "KAGGLE"
    source_record_id: str = ""
    domain: str = "E-commerce/Retail"
    channel: str = "Email"
    subject: str = ""
    message: str = Field(..., min_length=1)
