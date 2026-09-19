import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_user
from app.main import app
from app.models.enums import UserRole
from app.models.user import User


@pytest.fixture
def mock_db():
    session = MagicMock()
    return session


@pytest.fixture
def override_db(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield mock_db
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def override_current_user():
    """Default test authentication fixture providing an active Admin user."""
    now = datetime.now(timezone.utc)
    admin_user = User(
        id=uuid.uuid4(),
        email="testadmin@solwin.ai",
        full_name="Test Admin",
        hashed_password="mocked_password_hash",
        role=UserRole.ADMIN,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_current_active_user] = lambda: admin_user
    yield admin_user
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_user, None)
