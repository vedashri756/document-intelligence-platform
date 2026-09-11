from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import routes_documents, routes_health
from app.db.database import init_db
from app.exceptions import DocIntelError
from app.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Application started, database initialized.")
    yield


app = FastAPI(
    title="Document Intelligence Platform",
    description="Extraction, validation and API platform for invoices and financial statements.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Centralized exception handling (spec 9: fail gracefully, no stack traces) ---
@app.exception_handler(DocIntelError)
async def handle_docintel_error(request: Request, exc: DocIntelError):
    logger.warning(f"{exc.error_code}: {exc.message} | details={exc.details}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred while processing the request.",
        },
    )


app.include_router(routes_health.router)
app.include_router(routes_documents.router)

# Serve the static frontend at /
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
