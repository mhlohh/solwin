"""Global test environment isolation.

Tests must never depend on a developer's ``.env``. Force the AI provider off
and pin the default model *before* any ``ml_service`` import reads settings,
so unit tests (which supply their own keys) and integration tests (which
expect local-model behavior) are deterministic.
"""

import os

os.environ["GEMINI_ENABLED"] = "false"
os.environ["GEMINI_API_KEY"] = ""
os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"
