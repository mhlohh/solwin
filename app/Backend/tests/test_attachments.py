import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_active_user, get_current_user
from app.main import app
from app.models.attachment import Attachment
from app.models.conversation import Conversation
from app.models.enums import RiskLevel, UserRole
from app.models.message import Message
from app.models.user import User
from app.schemas.attachment import MultimodalAnalysisOutput
from app.schemas.unified import UnifiedAnalysisResponse
from app.services.attachments.local_storage import (
    LocalStorageBackend,
    get_storage_backend,
)
from app.services.attachments.validation import (
    calculate_sha256,
    sanitize_filename,
    validate_file_content,
)
from app.services.unified_intelligence import UnifiedIntelligenceService

# Sample valid byte contents
PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
WEBP_BYTES = b"RIFF\x14\x00\x00\x00WEBPVP8 \x08\x00\x00\x00"
PDF_BYTES = b"%PDF-1.4\n%test pdf content"
TEXT_BYTES = b"Hello, this is a plain text document."


# 1. Valid PNG accepted
def test_valid_png_accepted():
    filename, mime = validate_file_content(PNG_BYTES, "screenshot.png", "image/png")
    assert filename == "screenshot.png"
    assert mime == "image/png"


# 2. Valid JPEG accepted
def test_valid_jpeg_accepted():
    filename, mime = validate_file_content(JPEG_BYTES, "photo.jpg", "image/jpeg")
    assert filename == "photo.jpg"
    assert mime == "image/jpeg"


# 3. Valid WEBP accepted
def test_valid_webp_accepted():
    filename, mime = validate_file_content(WEBP_BYTES, "image.webp", "image/webp")
    assert filename == "image.webp"
    assert mime == "image/webp"


# 4. PDF accepted
def test_valid_pdf_accepted():
    filename, mime = validate_file_content(PDF_BYTES, "document.pdf", "application/pdf")
    assert filename == "document.pdf"
    assert mime == "application/pdf"


# 5. Plain text accepted
def test_valid_plain_text_accepted():
    filename, mime = validate_file_content(TEXT_BYTES, "notes.txt", "text/plain")
    assert filename == "notes.txt"
    assert mime == "text/plain"


# 6. Oversized file rejected
def test_oversized_file_rejected():
    huge_data = b"X" * (10 * 1024 * 1024 + 1)
    with pytest.raises(HTTPException) as exc:
        validate_file_content(huge_data, "large.txt", "text/plain")
    assert exc.value.status_code == 400
    assert "exceeds maximum allowed size" in exc.value.detail


# 7. Empty file rejected
def test_empty_file_rejected():
    with pytest.raises(HTTPException) as exc:
        validate_file_content(b"", "empty.png", "image/png")
    assert exc.value.status_code == 400
    assert "cannot be empty" in exc.value.detail


# 8. Unsupported MIME rejected
def test_unsupported_mime_rejected():
    with pytest.raises(HTTPException) as exc:
        validate_file_content(b"test", "script.sh", "application/x-sh")
    assert exc.value.status_code == 400
    assert "Unsupported file type" in exc.value.detail


# 9. Invalid image signature rejected
def test_invalid_image_signature_rejected():
    fake_png = b"NOT_A_PNG_CONTENT"
    with pytest.raises(HTTPException) as exc:
        validate_file_content(fake_png, "fake.png", "image/png")
    assert exc.value.status_code == 400
    assert "Invalid PNG file signature" in exc.value.detail


# 10. Filename path traversal sanitized/rejected
def test_filename_path_traversal_sanitized():
    sanitized = sanitize_filename("../../../etc/passwd")
    assert "/" not in sanitized
    assert ".." not in sanitized
    assert sanitized == "passwd"

    sanitized_win = sanitize_filename("..\\..\\boot.ini")
    assert "\\" not in sanitized_win
    assert sanitized_win == "boot.ini"


# 11. SHA-256 checksum generated
def test_sha256_checksum_generated():
    data = b"solwin-secure-attachment"
    checksum = calculate_sha256(data)
    assert len(checksum) == 64
    assert checksum == calculate_sha256(io.BytesIO(data))


# 12. Attachment metadata persisted & 13. Attachment associated with message
@pytest.mark.asyncio
async def test_attachment_upload_and_persistence(override_db, tmp_path):
    conv_id = uuid.uuid4()
    msg_id = uuid.uuid4()

    # Mock conversation & message existence in DB
    mock_conv = Conversation(id=conv_id)
    mock_msg = Message(id=msg_id, conversation_id=conv_id)

    override_db.scalar.side_effect = [
        mock_conv,
        mock_msg,
    ]

    backend = LocalStorageBackend(base_dir=tmp_path)
    app.dependency_overrides[get_storage_backend] = lambda: backend
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            files = {
                "file": ("test.png", PNG_BYTES, "image/png"),
            }
            res = await client.post(
                f"/api/v1/conversations/{conv_id}/messages/{msg_id}/attachments",
                files=files,
            )
            assert res.status_code == 201
            data = res.json()
            assert data["original_filename"] == "test.png"
            assert data["content_type"] == "image/png"
            assert data["file_size"] == len(PNG_BYTES)
            assert data["checksum"] == calculate_sha256(PNG_BYTES)
            assert data["conversation_id"] == str(conv_id)
            assert data["message_id"] == str(msg_id)
    finally:
        app.dependency_overrides.pop(get_storage_backend, None)


# 14. Unauthorized upload rejected
@pytest.mark.asyncio
async def test_unauthorized_upload_rejected(override_db):
    user = User(
        id=uuid.uuid4(),
        email="security@solwin.ai",
        role=UserRole.SECURITY_ANALYST,
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            files = {"file": ("test.png", PNG_BYTES, "image/png")}
            res = await client.post(
                f"/api/v1/conversations/{uuid.uuid4()}/messages/{uuid.uuid4()}/attachments",
                files=files,
            )
            assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_active_user, None)


# 15. Unauthorized download rejected
@pytest.mark.asyncio
async def test_unauthorized_download_rejected(override_db):
    inactive_user = User(
        id=uuid.uuid4(),
        email="inactive@solwin.ai",
        role=UserRole.SUPPORT_AGENT,
        is_active=False,
    )
    app.dependency_overrides[get_current_user] = lambda: inactive_user
    app.dependency_overrides[get_current_active_user] = lambda: (_ for _ in ()).throw(
        HTTPException(status_code=401, detail="User account is deactivated.")
    )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            res = await client.get(f"/api/v1/attachments/{uuid.uuid4()}")
            assert res.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_active_user, None)


# 16. Authorized download works
@pytest.mark.asyncio
async def test_authorized_download_works(override_db, tmp_path):
    att_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    storage_key = f"{conv_id}/{att_id}"

    backend = LocalStorageBackend(base_dir=tmp_path)
    await backend.save(storage_key, PNG_BYTES)

    att = Attachment(
        id=att_id,
        conversation_id=conv_id,
        original_filename="screenshot.png",
        content_type="image/png",
        file_size=len(PNG_BYTES),
        storage_key=storage_key,
        checksum=calculate_sha256(PNG_BYTES),
    )
    override_db.scalar.return_value = att

    app.dependency_overrides[get_storage_backend] = lambda: backend
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            res = await client.get(f"/api/v1/attachments/{att_id}")
            assert res.status_code == 200
            assert res.content == PNG_BYTES
            assert res.headers["content-type"] == "image/png"
    finally:
        app.dependency_overrides.pop(get_storage_backend, None)


# 17. Unauthorized deletion rejected
@pytest.mark.asyncio
async def test_unauthorized_deletion_rejected(override_db):
    agent_user = User(
        id=uuid.uuid4(),
        email="agent@solwin.ai",
        role=UserRole.SUPPORT_AGENT,
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: agent_user
    app.dependency_overrides[get_current_active_user] = lambda: agent_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            res = await client.delete(f"/api/v1/attachments/{uuid.uuid4()}")
            assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_active_user, None)


# 18. Authorized deletion works
@pytest.mark.asyncio
async def test_authorized_deletion_works(override_db, tmp_path):
    att_id = uuid.uuid4()
    storage_key = f"conv/{att_id}"
    backend = LocalStorageBackend(base_dir=tmp_path)
    await backend.save(storage_key, PNG_BYTES)

    att = Attachment(
        id=att_id,
        conversation_id=uuid.uuid4(),
        original_filename="screenshot.png",
        content_type="image/png",
        file_size=len(PNG_BYTES),
        storage_key=storage_key,
        checksum=calculate_sha256(PNG_BYTES),
    )
    override_db.scalar.return_value = att

    app.dependency_overrides[get_storage_backend] = lambda: backend
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            res = await client.delete(f"/api/v1/attachments/{att_id}")
            assert res.status_code == 204
            assert not await backend.exists(storage_key)
    finally:
        app.dependency_overrides.pop(get_storage_backend, None)


# 19. Missing attachment returns 404
@pytest.mark.asyncio
async def test_missing_attachment_returns_404(override_db):
    override_db.scalar.return_value = None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get(f"/api/v1/attachments/{uuid.uuid4()}")
        assert res.status_code == 404


# 20. Multimodal service is NOT called when no attachment exists
def test_multimodal_not_called_without_attachments(override_db):
    conv_id = uuid.uuid4()
    msg = Message(id=uuid.uuid4(), conversation_id=conv_id, content="Just text")
    msg.attachments = []
    conv = Conversation(id=conv_id, messages=[msg])

    with (
        patch(
            "app.services.unified_intelligence.ConversationService.get_conversation_detail",
            return_value=conv,
        ),
        patch(
            "app.services.unified_intelligence.MultimodalService.analyze_image"
        ) as mock_analyze_image,
        patch(
            "app.services.unified_intelligence.CustomerIntelligenceService.analyze_conversation"
        ) as mock_cust_ai,
        patch(
            "app.services.unified_intelligence.ConversationService.save_or_update_analysis"
        ),
        patch(
            "app.services.unified_intelligence.ConversationService.save_or_update_threat"
        ),
    ):
        mock_cust_ai.return_value = MagicMock(
            category="TECHNICAL_ISSUE",
            issue="Issue",
            sentiment="NEUTRAL",
            emotion="Neutral",
            priority="LOW",
            resolution_status="UNRESOLVED",
            summary="Summary",
        )
        UnifiedIntelligenceService.analyze_conversation(override_db, conv_id)
        mock_analyze_image.assert_not_called()


# 21. Multimodal service is called when supported image exists
def test_multimodal_called_with_image_attachment(override_db):
    conv_id = uuid.uuid4()
    att_id = uuid.uuid4()
    att = Attachment(
        id=att_id,
        conversation_id=conv_id,
        original_filename="screenshot.png",
        content_type="image/png",
        storage_key=f"{conv_id}/{att_id}",
        file_size=len(PNG_BYTES),
        checksum="dummy",
    )
    msg = Message(id=uuid.uuid4(), conversation_id=conv_id, content="See screenshot")
    msg.attachments = [att]
    conv = Conversation(id=conv_id, messages=[msg])

    mock_storage = AsyncMock()
    mock_storage.get.return_value = PNG_BYTES

    with (
        patch(
            "app.services.unified_intelligence.ConversationService.get_conversation_detail",
            return_value=conv,
        ),
        patch(
            "app.services.unified_intelligence.get_storage_backend",
            return_value=mock_storage,
        ),
        patch(
            "app.services.unified_intelligence.MultimodalService.analyze_image"
        ) as mock_analyze_image,
        patch(
            "app.services.unified_intelligence.CustomerIntelligenceService.analyze_conversation"
        ) as mock_cust_ai,
        patch(
            "app.services.unified_intelligence.ConversationService.save_or_update_analysis"
        ),
        patch(
            "app.services.unified_intelligence.ConversationService.save_or_update_threat"
        ),
    ):
        mock_analyze_image.return_value = MultimodalAnalysisOutput(
            visible_text="Error 500",
            customer_context="Server crashed",
            issue_indicators=["Error 500"],
        )
        mock_cust_ai.return_value = MagicMock(
            category="TECHNICAL_ISSUE",
            issue="Error 500 crash",
            sentiment="NEGATIVE",
            emotion="Frustration",
            priority="HIGH",
            resolution_status="UNRESOLVED",
            summary="Server crashed",
        )
        UnifiedIntelligenceService.analyze_conversation(override_db, conv_id)
        mock_analyze_image.assert_called_once()


# 22. Multimodal output validates against Pydantic schema
def test_multimodal_output_pydantic_schema():
    payload = {
        "visible_text": "Sign in with OTP at http://login-check.com",
        "customer_context": "Suspicious login dialogue",
        "issue_indicators": ["Login prompt"],
        "security_indicators": ["Credential harvesting form"],
        "attachment_summary": "Phishing login screen",
        "extracted_urls": ["http://login-check.com"],
        "extracted_emails": ["support@login-check.com"],
    }
    output = MultimodalAnalysisOutput.model_validate(payload)
    assert output.visible_text == payload["visible_text"]
    assert output.extracted_urls == ["http://login-check.com"]
    assert output.extracted_emails == ["support@login-check.com"]
    assert "Credential harvesting form" in output.security_indicators


# 23. Extracted URL is passed into existing security analysis
# 24. Existing RiskEngine responsible for final scoring
def test_extracted_url_passed_into_security_analysis_and_risk_engine(override_db):

    conv_id = uuid.uuid4()
    att_id = uuid.uuid4()
    att = Attachment(
        id=att_id,
        conversation_id=conv_id,
        original_filename="phishing_proof.png",
        content_type="image/png",
        storage_key=f"{conv_id}/{att_id}",
        file_size=len(PNG_BYTES),
        checksum="dummy",
    )
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        content="Look at this urgent message: enter your password right now",
    )
    msg.attachments = [att]
    conv = Conversation(id=conv_id, messages=[msg])

    mock_storage = AsyncMock()
    mock_storage.get.return_value = PNG_BYTES

    with (
        patch(
            "app.services.unified_intelligence.ConversationService.get_conversation_detail",
            return_value=conv,
        ),
        patch(
            "app.services.unified_intelligence.get_storage_backend",
            return_value=mock_storage,
        ),
        patch(
            "app.services.unified_intelligence.MultimodalService.analyze_image"
        ) as mock_analyze_image,
        patch(
            "app.services.unified_intelligence.CustomerIntelligenceService.analyze_conversation"
        ) as mock_cust_ai,
        patch(
            "app.services.unified_intelligence.ConversationService.save_or_update_analysis"
        ),
        patch(
            "app.services.unified_intelligence.ConversationService.save_or_update_threat"
        ),
    ):
        # Multimodal extracts a suspicious phishing url from image
        mock_analyze_image.return_value = MultimodalAnalysisOutput(
            visible_text="Please verify at http://192.168.1.1/login.php",
            customer_context="Account verification popup",
            extracted_urls=["http://192.168.1.1/login.php"],
        )
        mock_cust_ai.return_value = MagicMock(
            category="ACCOUNT_ACCESS",
            issue="Account verification issue",
            sentiment="NEUTRAL",
            emotion="Confusion",
            priority="MEDIUM",
            resolution_status="UNRESOLVED",
            summary="Customer asks about verification popup",
        )

        res: UnifiedAnalysisResponse = UnifiedIntelligenceService.analyze_conversation(
            override_db, conv_id
        )

        # Risk engine should have caught the IP-based URL extracted from image
        assert res.security_intelligence.threat_detected is True
        assert res.security_intelligence.risk_level in [
            RiskLevel.HIGH.value,
            RiskLevel.CRITICAL.value,
        ]
        assert any(
            "192.168.1.1" in u for u in res.security_intelligence.suspicious_urls
        )
