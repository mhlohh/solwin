"""Container entrypoint helper: optional migration bootstrap before API start.

Behavior is controlled by the RUN_MIGRATIONS environment variable:
- unset/0  -> start the API immediately (default; matches current behavior)
- "1"      -> run `alembic upgrade head` first (recommended on Cloud SQL)

On any failure the API still boots: the platform health check decides
readiness, and Alembic logs the underlying error for debugging.
"""

import os
import subprocess
import sys

import uvicorn

if __name__ == "__main__":
    if os.getenv("RUN_MIGRATIONS", "0") == "1":
        print("RUN_MIGRATIONS=1 -> applying alembic migrations...", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        if result.returncode != 0:
            print(
                "alembic upgrade failed; starting API anyway (health check will "
                "report actual readiness).",
                flush=True,
            )

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8001")),
        log_level=os.getenv("LOG_LEVEL", "info"),
    )
