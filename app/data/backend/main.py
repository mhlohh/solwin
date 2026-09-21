import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base, SessionLocal
from .seed import seed_database
from .routers import tickets, attachments

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic: create tables & seed DB
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    except Exception as e:
        print(f"Error during database startup seed: {e}")
    finally:
        db.close()
    yield
    # Shutdown logic (if any)

app = FastAPI(
    title="Customer Support & Phishing Intelligence API Service",
    description="RESTful API service for ingesting, managing, and attachment-enriching customer support & phishing ticket data.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tickets.router)
app.include_router(attachments.router)

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Customer Support & Phishing Intelligence API",
        "status": "online",
        "docs": "/docs"
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
