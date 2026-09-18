import os
import sys
from sqlalchemy.orm import Session

from .database import engine, SessionLocal, Base
from .models import Ticket
from .clean_data import clean_csv_data


def _coerce_phishing(value) -> bool | None:
    """Coerce dataset phishing flags ('True'/'False'/'1'/'0'/bool) to bool."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes")


def seed_database(db: Session, file_path: str = None, batch_size: int = 1000):
    """
    Populates the database with cleaned CSV data if the tickets table is empty.
    """
    existing_count = db.query(Ticket).count()
    if existing_count > 0:
        print(f"Database already populated ({existing_count} tickets existing). Skipping seed.")
        return

    print("Seeding database with cleaned CSV dataset...")
    df = clean_csv_data(file_path=file_path)

    records = df.to_dict(orient="records")
    total_records = len(records)
    print(f"Inserting {total_records} records into database in batches of {batch_size}...")

    # Batch insert for fast performance
    for i in range(0, total_records, batch_size):
        batch = records[i:i + batch_size]
        ticket_objects = [
            Ticket(
                message=r.get("message", ""),
                domain=r.get("domain", ""),
                channel=r.get("channel", ""),
                subject=r.get("subject", ""),
                intent=r.get("intent", ""),
                issue=r.get("issue", ""),
                technique=r.get("technique", ""),
                phishing=_coerce_phishing(r.get("phishing")),
                sender=r.get("sender", ""),
                label=r.get("label", "")
            )
            for r in batch
        ]
        db.bulk_save_objects(ticket_objects)
        db.commit()

    print(f"Successfully seeded {total_records} ticket records.")


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

if __name__ == "__main__":
    main()
