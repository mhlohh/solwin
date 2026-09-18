"""Portable column types shared by all models.

``Uuid`` renders the native UUID type on PostgreSQL and CHAR(36) on SQLite
(local development and tests), with proper bind handling in both cases.
JSONB keeps native JSON storage on PostgreSQL and falls back to JSON on
SQLite. No behaviour change on PostgreSQL.
"""

from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB

UUIDType = Uuid(as_uuid=True)
JSONType = JSONB().with_variant(JSON(), "sqlite")

__all__ = ["UUIDType", "JSONType"]
