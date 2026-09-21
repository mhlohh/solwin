# Customer Support & Phishing Intelligence REST API Service

A containerized Python **FastAPI** service with **PostgreSQL** database, **SQLAlchemy** ORM, automated CSV data preprocessing & seeding, and file attachment handling (PDFs and Images) with strict MIME validation.

---

## Tech Stack

* **Backend Framework:** Python 3.11 with FastAPI
* **Database:** PostgreSQL 15
* **ORM:** SQLAlchemy 2.0
* **Data Processing:** Pandas
* **Containerization:** Docker & Docker Compose

---

## Repository Structure

```
.
├── docs/
│   └── schema.md                        # Database schema documentation
├── app/
│   ├── data/
│   │   ├── unified_customer_phishing_data_subset.csv       # Source dataset
│   │   └── unified_customer_phishing_data_subset (1).csv   # Raw dataset
│   └── backend/
│       ├── main.py                      # FastAPI application entry point
│       ├── database.py                  # SQLAlchemy engine & session management
│       ├── models.py                    # DB Models (Ticket & Attachment)
│       ├── schemas.py                   # Pydantic validation schemas
│       ├── crud.py                      # Database access operations
│       ├── clean_data.py                # CSV cleaning & deduplication
│       ├── seed.py                      # Automated DB seeding script
│       ├── routers/
│       │   ├── tickets.py               # Ticket CRUD endpoints
│       │   └── attachments.py           # File upload/download endpoints
│       └── requirements.txt             # Python dependencies
├── Dockerfile                           # Multi-stage container build file
├── docker-compose.yml                   # Service orchestration config
└── README.md                            # Comprehensive service documentation
```

---

## Features & Requirements Compliance

1. **Data Preprocessing & Seeding**:
   - `clean_data.py` ingests `unified_customer_phishing_data_subset.csv`, fills missing (`NaN`) values with empty strings, strips whitespace across all fields (`message`, `subject`, `intent`, `issue`), and removes duplicate records.
   - `seed.py` runs automatically on startup when the database container launches, inserting batch-cleaned records into PostgreSQL if the table is empty.

2. **Relational Database Schema**:
   - **`tickets`**: Stores `id`, `message`, `subject`, `intent`, `issue`, and `created_at`.
   - **`attachments`**: Stores metadata for uploaded files: `id`, `ticket_id` (FK with CASCADE delete), `file_name`, `file_type`, `file_path`, `file_size`, and `created_at`.
   - Detailed schema docs can be found at [docs/schema.md](docs/schema.md).

3. **Strict MIME Type Validation**:
   - Enforces strict validation for uploads. Accepted types: `application/pdf` (`.pdf`), `image/png` (`.png`), `image/jpeg` (`.jpeg`, `.jpg`).
   - Rejects unauthorized file formats with `400 Bad Request`.

4. **Full CRUD & Attachment Storage**:
   - Comprehensive REST API endpoints for Ticket management and linked file uploads/downloads.

---

## Quick Start (Docker Compose)

### 1. Launch Services
Run the following command in the workspace root:

```bash
docker-compose up --build -d
```

This will build the FastAPI backend container, launch PostgreSQL, execute health checks, and auto-seed the dataset into PostgreSQL.

### 2. Check Service Logs
To inspect DB seeding and application logs:

```bash
docker-compose logs -f backend
```

### 3. Access Interactive API Docs
Open your browser and navigate to:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 4. Stop Services
To stop and remove containers:

```bash
docker-compose down -v
```

---

## API Endpoints Reference

### Health & System
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | API status & metadata |
| `GET` | `/health` | Health check probe |

### Tickets CRUD
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/tickets` | List tickets with pagination (`skip`, `limit`) and filtering (`intent`, `search`) |
| `GET` | `/tickets/{ticket_id}` | Retrieve details of a single ticket (includes attachments) |
| `POST` | `/tickets` | Create a new ticket record |
| `PUT` | `/tickets/{ticket_id}` | Update an existing ticket record |
| `DELETE` | `/tickets/{ticket_id}` | Delete a ticket and cascade delete its attachments |

### File Attachments
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/tickets/{ticket_id}/attachments` | Upload a PDF or Image (PNG/JPEG) attachment for a ticket |
| `GET` | `/tickets/{ticket_id}/attachments` | List all attachments belonging to a ticket |
| `GET` | `/attachments/{attachment_id}` | Retrieve/download an attachment file |
| `DELETE` | `/attachments/{attachment_id}` | Delete an attachment file and DB metadata record |

---

## Testing Guide with `curl` Commands

### 1. Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

---

### 2. List Tickets (Pagination & Filtering)
Fetch default list (first 5 items):
```bash
curl -X GET "http://localhost:8000/tickets?skip=0&limit=5"
```

Filter tickets by intent (e.g., `Fraudulent User`):
```bash
curl -X GET "http://localhost:8000/tickets?intent=Fraudulent%20User&limit=3"
```

Search tickets by keyword:
```bash
curl -X GET "http://localhost:8000/tickets?search=Exchange&limit=3"
```

---

### 3. Create a Ticket
```bash
curl -X POST "http://localhost:8000/tickets" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Suspicious Login Alert",
    "message": "User reported unexpected account access attempt from unauthorized IP.",
    "intent": "Fraudulent User",
    "issue": "Phishing Attempt"
  }'
```

---

### 4. Get Ticket Details by ID
```bash
curl -X GET "http://localhost:8000/tickets/1"
```

---

### 5. Update a Ticket
```bash
curl -X PUT "http://localhost:8000/tickets/1" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Updated - Suspicious Login Alert",
    "issue": "Verified Phishing Attempt - Escalated"
  }'
```

---

### 6. File Attachments Testing

#### A. Upload PDF Attachment
Create a sample PDF file and attach it to ticket ID `1`:
```bash
# Create dummy sample PDF for testing
echo "%PDF-1.4 dummy content" > sample_document.pdf

curl -X POST "http://localhost:8000/tickets/1/attachments" \
  -F "file=@sample_document.pdf;type=application/pdf"
```

#### B. Upload PNG Image Attachment
Create a sample image file and attach it to ticket ID `1`:
```bash
# Create dummy sample image for testing
echo "fake image bytes" > screenshot.png

curl -X POST "http://localhost:8000/tickets/1/attachments" \
  -F "file=@screenshot.png;type=image/png"
```

#### C. Test Invalid MIME-Type Rejection (Validation Check)
Attempting to upload an unsupported format (e.g., `.txt` or `text/plain`):
```bash
echo "Unauthorized content" > bad_file.txt

curl -X POST "http://localhost:8000/tickets/1/attachments" \
  -F "file=@bad_file.txt;type=text/plain"
```
*Expected Response:* `400 Bad Request` with error details.

#### D. List Attachments for a Ticket
```bash
curl -X GET "http://localhost:8000/tickets/1/attachments"
```

#### E. Download an Attachment File
Download attachment ID `1` to local file `downloaded_attachment.pdf`:
```bash
curl -X GET "http://localhost:8000/attachments/1" --output downloaded_attachment.pdf
```

#### F. Delete an Attachment
```bash
curl -X DELETE "http://localhost:8000/attachments/1"
```

---

### 7. Delete a Ticket
Delete ticket ID `1` (which also cascades deletion to linked attachments):
```bash
curl -X DELETE "http://localhost:8000/tickets/1"
```