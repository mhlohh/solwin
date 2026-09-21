# Database Schema Documentation

This document describes the database schema for the Customer Support & Phishing Intelligence REST API service.

---

## Entity Relationship Summary

```
+------------------------------------+          +--------------------------------------+
|              tickets               |          |             attachments              |
+------------------------------------+          +--------------------------------------+
| id          : INTEGER (PK, AUTO)   | 1      * | id          : INTEGER (PK, AUTO)     |
| subject     : VARCHAR(255)         |<--------| ticket_id   : INTEGER (FK, CASCADE)  |
| message     : TEXT                 |          | file_name   : VARCHAR(255)         |
| intent      : VARCHAR(100)         |          | file_type   : VARCHAR(100)         |
| issue       : VARCHAR(255)         |          | file_path   : VARCHAR(512)         |
| created_at  : TIMESTAMP (UTC)      |          | file_size   : INTEGER              |
+------------------------------------+          | created_at  : TIMESTAMP (UTC)        |
                                                +--------------------------------------+
```

---

## 1. Table: `tickets`

Stores cleaned customer support and phishing message data.

| Column Name | Data Type | Nullable | Primary / Foreign Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | **No** | Primary Key (Auto-Increment) | Unique ticket identifier |
| `subject` | `VARCHAR(255)` | Yes | - | Subject line of the ticket |
| `message` | `TEXT` | **No** | - | Ticket message content |
| `intent` | `VARCHAR(100)` | Yes | Index | Categorized intent (e.g. `Exchange / Replacement`, `Fraudulent User`, `Delayed`) |
| `issue` | `VARCHAR(255)` | Yes | Index | Specific issue description |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | **No** | - | Server timestamp when the record was created (UTC) |

### Indexes & Constraints
- `pk_tickets`: Primary key constraint on `id`.
- `idx_tickets_intent`: B-tree index on `intent` for fast filtering.
- `idx_tickets_issue`: B-tree index on `issue` for fast filtering.

---

## 2. Table: `attachments`

Stores metadata for PDF and Image attachments associated with tickets.

| Column Name | Data Type | Nullable | Primary / Foreign Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | **No** | Primary Key (Auto-Increment) | Unique attachment identifier |
| `ticket_id` | `INTEGER` | **No** | Foreign Key (`tickets.id` ON DELETE CASCADE) | ID of the ticket this attachment belongs to |
| `file_name` | `VARCHAR(255)` | **No** | - | Original uploaded filename |
| `file_type` | `VARCHAR(100)` | **No** | - | MIME type (`application/pdf`, `image/png`, `image/jpeg`, `image/jpg`) |
| `file_path` | `VARCHAR(512)` | **No** | - | Storage path on disk (`/app/uploads/<uuid>_<filename>`) |
| `file_size` | `INTEGER` | **No** | - | Size of the file in bytes |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | **No** | - | Timestamp when the attachment was uploaded (UTC) |

### Indexes & Constraints
- `pk_attachments`: Primary key constraint on `id`.
- `fk_attachments_ticket_id`: Foreign key referencing `tickets(id)` with `ON DELETE CASCADE`.
- `idx_attachments_ticket_id`: Index on `ticket_id` to quickly fetch attachments for a given ticket.

---

## Supported File MIME Types
Strict validation is enforced on upload:
- `application/pdf` (.pdf)
- `image/png` (.png)
- `image/jpeg` (.jpeg, .jpg)
