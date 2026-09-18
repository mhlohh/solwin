"""One-shot local bootstrap: create tables and seed demo data.

Usage (from app/Backend):
    uv run python scripts/bootstrap_local.py

Creates the database (per DATABASE_URL, default SQLite solwin_dev.db) with:
- a demo agent user (FK target for assigned conversations)
- 6 realistic conversations across channels with customer messages
- real Gemini customer intelligence per conversation (falls back to skipping
  that record if the API is unavailable)
- deterministic security/threat analysis via the local RiskEngine

Safe to re-run: skips seeding when conversations already exist.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.models.conversation import Conversation  # noqa: E402
from app.models.enums import (  # noqa: E402
    ConversationChannel,
    ConversationStatus,
    SenderType,
)
from app.models.message import Message  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.ai.customer_intelligence import (  # noqa: E402
    CustomerIntelligenceService,
)
from app.services.conversation_service import ConversationService  # noqa: E402
from app.services.security.risk_engine import RiskEngine  # noqa: E402

DEMO_CONVERSATIONS = [
    {
        "customer_name": "Sarah Mitchell",
        "customer_email": "sarah.mitchell@example.com",
        "channel": ConversationChannel.EMAIL,
        "subject": "Account locked after password reset",
        "status": ConversationStatus.OPEN,
        "initial_message": (
            "I tried to log in this morning and my account is locked. "
            "I received a password reset email that I never requested last night. "
            "Please help me regain access urgently, I have orders pending."
        ),
    },
    {
        "customer_name": "David Chen",
        "customer_email": "david.chen@example.com",
        "channel": ConversationChannel.CHAT,
        "subject": "Order #58291 not delivered",
        "status": ConversationStatus.IN_PROGRESS,
        "initial_message": (
            "Hi, my order 58291 was supposed to arrive three days ago but the "
            "tracking hasn't updated. Could you check what's going on? This is "
            "really frustrating as it was a gift."
        ),
    },
    {
        "customer_name": "Amara Okafor",
        "customer_email": "amara.okafor@example.com",
        "channel": ConversationChannel.EMAIL,
        "subject": "Suspicious login alert from unknown device",
        "status": ConversationStatus.OPEN,
        "initial_message": (
            "I got an alert about a login from a device in another country. "
            "I did not log in and I received an email asking for my one-time "
            "password to stop the login. Someone may have stolen my password. "
            "Please secure my account and tell me what information was accessed."
        ),
    },
    {
        "customer_name": "Tom Bailey",
        "customer_email": "tom.bailey@example.com",
        "channel": ConversationChannel.TICKET,
        "subject": "Refund not received for cancelled subscription",
        "status": ConversationStatus.RESOLVED,
        "initial_message": (
            "I cancelled my subscription two weeks ago and was promised a refund "
            "within 5 business days but nothing has arrived. Kindly process it "
            "or share the transaction reference."
        ),
    },
    {
        "customer_name": "Lena Fischer",
        "customer_email": "lena.fischer@example.com",
        "channel": ConversationChannel.SOCIAL_MEDIA,
        "subject": "Payment card charged twice",
        "status": ConversationStatus.IN_PROGRESS,
        "initial_message": (
            "Your payment page charged my card twice for the same order! "
            "I need one charge reversed today. This looks like a billing error "
            "and I'm seriously considering reporting it to my bank."
        ),
    },
    {
        "customer_name": "Raj Patel",
        "customer_email": "raj.patel@example.com",
        "channel": ConversationChannel.CHAT,
        "subject": "Cannot upload attachments in support portal",
        "status": ConversationStatus.CLOSED,
        "initial_message": (
            "The support portal fails when I try to attach a screenshot. "
            "The upload spinner runs forever and then shows an error. "
            "Tried two browsers already. Thanks for looking into it."
        ),
    },
]


def seed_analysis(
    db, conv: Conversation, subject: str, messages: list, gemini_ok: bool
) -> None:
    """Run Gemini + RiskEngine and persist results; tolerate AI outages."""
    if gemini_ok:
        try:
            intel = CustomerIntelligenceService().analyze_conversation(
                messages=messages, subject=subject
            )
            ConversationService.save_or_update_analysis(db, conv.id, intel)
        except Exception as exc:  # noqa: BLE001 - seed must survive AI outages
            print(f"    ! customer intelligence skipped: {exc}")
    else:
        print("    ! customer intelligence skipped (Gemini unavailable)")

    try:
        aggregated = "\n".join(
            f"[{m.sender_type.value}] {m.content}" for m in messages
        )
        sec = RiskEngine().evaluate(text=aggregated)
        ConversationService.save_or_update_threat(db, conv.id, sec)
    except Exception as exc:  # noqa: BLE001
        print(f"    ! threat analysis skipped: {exc}")


def main() -> int:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing = db.query(Conversation).count()
        if existing:
            print(f"Database already seeded ({existing} conversations). Nothing to do.")
            return 0

        agent = db.query(User).filter(User.email == "agent@solwin.local").first()
        if not agent:
            agent = User(
                email="agent@solwin.local",
                full_name="Demo Agent",
                hashed_password="not-used-no-auth",
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)

        now = datetime.now(timezone.utc)
        gemini_ok = bool(
            __import__("app.core.config", fromlist=["get_settings"])
            .get_settings()
            .GEMINI_API_KEY
        )

        for i, spec in enumerate(DEMO_CONVERSATIONS):
            created = now - timedelta(days=6 - i, hours=i)
            conv = Conversation(
                conversation_reference=f"CONV-{i + 1:06d}",
                customer_name=spec["customer_name"],
                customer_email=spec["customer_email"],
                channel=spec["channel"],
                subject=spec["subject"],
                status=spec["status"],
                assigned_agent_id=agent.id if i % 2 == 0 else None,
                created_at=created,
                updated_at=created,
            )
            db.add(conv)
            db.flush()

            msg = Message(
                conversation_id=conv.id,
                sender_type=SenderType.CUSTOMER,
                sender_name=spec["customer_name"],
                content=spec["initial_message"],
                created_at=created,
            )
            db.add(msg)
            db.flush()

            print(f"  + {conv.conversation_reference}: {spec['subject']}")
            seed_analysis(db, conv, spec["subject"], [msg], gemini_ok)

        db.commit()
        total = db.query(Conversation).count()
        print(f"Seeded {total} conversations into {engine.url}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
