# Deploying Solwin to Google Cloud

Everything in the stack is containerized — four images plus Postgres. The
fastest production-ready path is **Cloud Run + Cloud SQL**, deployed from
images built by **Cloud Build** into **Artifact Registry**.

## Architecture

| Image (`solwin/` in Artifact Registry) | Source | Role | Container port |
|---|---|---|---|
| `frontend` | `app/frontend/Dockerfile` | nginx: SPA + reverse proxy for both APIs | 8080 |
| `backend` | `app/Backend/Dockerfile` | FastAPI: conversations, unified AI, dashboard | 8001 |
| `ml-service` | `app/ml_services/Dockerfile` | sklearn + Gemini inference (canonical review schema) | 8000 |
| `data-api` | `app/data/Dockerfile` | Raw feedback dataset: inbox, priority queue, stats | 8000 |
| `postgres:16` | Cloud SQL (managed) | Databases for Backend + Data API | 5432 |

Traffic flow: **browser → frontend container only**. nginx proxies
`/api/*` → backend and `/data-api/*` → data-api, so only the frontend
service needs public ingress.

## 0. Prerequisites (one-time)

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com

# Artifact Registry repo for the four images
gcloud artifacts repositories create solwin \
  --repository-format=docker --location=us-central1

# Let Cloud Build push images and let the compute SA pull them
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
  --role=roles/artifactregistry.writer
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --role=roles/artifactregistry.reader
```

## 1. Database — Cloud SQL (Postgres 16)

```bash
gcloud sql instances create solwin-db \
  --database-version=POSTGRES_16 --tier=db-f1-micro \
  --region=us-central1 --storage-auto-increase

gcloud sql users create solwin --instance=solwin-db \
  --password="$(openssl rand -base64 24)"   # store it in Secret Manager

gcloud sql databases create solwin --instance=solwin-db
gcloud sql databases create solwin_data --instance=solwin-db
```

Store the connection strings once, read by the services at boot:

```bash
printf 'postgresql+psycopg2://solwin:PASSWORD@localhost/solwin?host=/cloudsql/PROJECT:us-central1:solwin-db' \
  | gcloud secrets create solwin-database-url --data-file=-
printf 'postgresql://solwin:PASSWORD@localhost/solwin_data?host=/cloudsql/PROJECT:us-central1:solwin-db' \
  | gcloud secrets create solwin-data-database-url --data-file=-
```

(`?host=/cloudsql/...` is the Unix-socket form used with
`--add-cloudsql-instances` below.)

## 2. Gemini key — Secret Manager

```bash
printf 'YOUR_KEY' | gcloud secrets create gemini-api-key --data-file=-
```

## 3. Build all four images

```bash
gcloud builds submit --config deploy/cloudbuild.yaml .
```

## 4. Deploy

```bash
REGION=us-central1
PROJECT=YOUR_PROJECT_ID
REG=us-central1-docker.pkg.dev/$PROJECT/solwin

# 4a. ML service (internal ingress; only the backend calls it).
# Trained sklearn models are already baked into the image.
gcloud run deploy solwin-ml \
  --image=$REG/ml-service:latest --region=$REGION \
  --ingress=internal \
  --cpu=1 --memory=1Gi

# 4b. Data API (internal ingress; frontend proxies it)
gcloud run deploy solwin-data-api \
  --image=$REG/data-api:latest --region=$REGION \
  --ingress=internal \
  --add-cloudsql-instances=PROJECT:us-central1:solwin-db \
  --set-secrets=DATABASE_URL=solwin-data-database-url:latest \
  --cpu=1 --memory=1Gi

# 4c. Backend (internal ingress; frontend proxies it)
gcloud run deploy solwin-backend \
  --image=$REG/backend:latest --region=$REGION \
  --ingress=internal \
  --add-cloudsql-instances=PROJECT:us-central1:solwin-db \
  --set-secrets=DATABASE_URL=solwin-database-url:latest \
  --set-env-vars=ML_SERVICE_URL=https://solwin-ml-xxxxxxxx-uc.a.run.app \
  --cpu=1 --memory=1Gi \
  --min-instances=0 --max-instances=5

# 4d. Frontend — the public entry point
gcloud run deploy solwin-frontend \
  --image=$REG/frontend:latest --region=$REGION \
  --ingress=all \
  --set-env-vars=BACKEND_SERVICE_URL=https://solwin-backend-xxxxxxxx-uc.a.run.app,DATA_SERVICE_URL=https://solwin-data-api-xxxxxxxx-uc.a.run.app \
  --cpu=1 --memory=512Mi
```

(The `xxxxxxxx` URLs come from the deploy outputs of steps 4b/4c.)

Open the `solwin-frontend` URL — the whole app is served from that one origin.

## 5. Environment variables & secrets reference

| Service | Variable | Source |
|---|---|---|
| backend | `DATABASE_URL` | Secret `solwin-database-url` |
| backend | `ML_SERVICE_URL` | ML service URL from step 4a |
| backend | `DATA_SERVICE_URL` | Data API URL from step 4b |
| backend | `GEMINI_API_KEY` | Secret `gemini-api-key` |
| backend | `RUN_MIGRATIONS=1` | Optional: apply Alembic on boot |
| data-api | `DATABASE_URL` | Secret `solwin-data-database-url` |
| data-api | `UPLOAD_DIR` | defaults to `/app/uploads` |
| frontend | `BACKEND_SERVICE_URL` | Backend URL (rendered into nginx config at start) |
| frontend | `DATA_SERVICE_URL` | Data API URL (rendered into nginx config at start) |

## 6. Seed the dataset (Data API)

The data-api container ships with the 5.6 MB CSV and **auto-seeds its
database on first boot** (`main.py` lifespan). On Cloud SQL this happens
when the first request arrives after deploy; 20,862 records insert in well
under a minute.

## Local end-to-end (compose)

```bash
cp .env.example .env        # fill in GEMINI_API_KEY
docker compose up --build
# app:    http://localhost:8080
# API:    http://localhost:8001/docs
```

## Notes

- **ML models**: the ML image copies `app/ml_services/models` at build time —
  no model upload step needed.
- **Frontend routing**: the nginx config is a template rendered at container
  start from `BACKEND_SERVICE_URL` / `DATA_SERVICE_URL`, so the identical
  image serves both compose (service names) and Cloud Run (service URLs).
- **Rollbacks** are trivial since every image is tagged with `$COMMIT_SHA`:
  `gcloud run deploy solwin-frontend --image=$REG/frontend:OLD_SHA`.
- If you prefer **GKE**: the same four images deploy as a Deployment+Service
  per component; the env vars in section 5 are all that changes.
