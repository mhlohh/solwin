from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AttachmentBase(BaseModel):
    original_filename: str
    content_type: str
    file_size: int


class AttachmentRead(BaseModel):
    id: UUID
    conversation_id: UUID
    message_id: UUID | None = None
    original_filename: str
    content_type: str
    file_size: int
    checksum: str
    created_at: datetime
    width: int | None = None
    height: int | None = None
    page_count: int | None = None

    model_config = ConfigDict(from_attributes=True)


class MultimodalAnalysisOutput(BaseModel):
    """Structured Pydantic response model for Gemini multimodal analysis."""

    visible_text: str = Field(
        default="",
        description="Text extracted directly from image, document or screenshot",
    )
    customer_context: str = Field(
        default="",
        description="Summary of customer issue or situation from attachment",
    )
    issue_indicators: list[str] = Field(
        default_factory=list,
        description="Key problem or failure indicators spotted in the visual",
    )
    security_indicators: list[str] = Field(
        default_factory=list,
        description="Potential security concerns, OTP prompts, or credentials",
    )

    attachment_summary: str = Field(
        default="",
        description="Concise description of the attachment contents",
    )
    extracted_urls: list[str] = Field(
        default_factory=list,
        description="Specific URLs spotted in the attachment",
    )
    extracted_emails: list[str] = Field(
        default_factory=list,
        description="Specific email addresses spotted in the attachment",
    )
