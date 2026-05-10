from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from config import Config
from data_models import LetterRequest
from pipe_liner import LetterGenerationPipeline
from knowledge_base import KnowledgeBase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("dabirkhane.api")
pipeline: Optional[LetterGenerationPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    logger.info("Starting up — building pipeline...")
    try:
        pipeline = LetterGenerationPipeline(Config())
        logger.info("Pipeline ready.")
    except Exception as e:
        logger.error(f"Pipeline build failed: {e}")
        raise
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Dabirkhane — Administrative Letter Generation System",
    description=(
        "An intelligent API for generating Persian administrative letters "
        "using RAG, LangGraph, and an LLM."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    from_role: Optional[str] = Field(
        default=None,
        examples=["Employee"],
        description="Sender role",
    )
    to_role: Optional[str] = Field(
        default=None,
        examples=["Manager"],
        description="Recipient role",
    )
    subject: str = Field(
        ...,
        min_length=3,
        max_length=200,
        examples=["Request for salary increase"],
        description="Letter subject",
    )
    purpose: str = Field(
        ...,
        min_length=5,
        max_length=500,
        examples=["Submitting a formal request for review of salary increase"],
        description="Purpose of the letter",
    )
    details: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        examples=[
            "Given the 40% inflation rate, 5 years of service, "
            "and excellent performance evaluation in 2024, I request a 25% salary increase."
        ],
        description="Full details for text generation — the more precise, the better the result",
    )
    tone: Optional[str] = Field(
        default=None,
        examples=["respectful_formal"],
        description="Tone; if empty, the system will detect it automatically",
    )
    date: Optional[str] = Field(
        default=None,
        examples=["2025/05/14"],
        description="Letter date; if empty, today's date will be used",
    )
    org_name: Optional[str] = Field(
        default=None,
        examples=["Sample Company"],
        description="Organization name",
    )
    language: str = Field(default="en", description="Output language")
    length: str = Field(
        default="medium",
        examples=["small", "medium", "big"],
        description="Letter length: small (80–120 words) | medium (150–250 words) | big (300–450 words)",
    )

    @field_validator("length")
    @classmethod
    def validate_length(cls, v: str) -> str:
        allowed = {"small", "medium", "big"}
        if v not in allowed:
            raise ValueError(f"length must be one of {allowed}.")
        return v

    @field_validator("details")
    @classmethod
    def details_must_be_specific(cls, v: str) -> str:
        vague_phrases = ["please", "kindly", "thanks"]
        word_count = len(v.split())
        if word_count < 8:
            raise ValueError(
                "details must contain at least 8 words to generate a high-quality letter."
            )
        return v


class GenerateResponse(BaseModel):

    request_id: str = Field(..., description="Unique request identifier")
    letter: str = Field(..., description="Final letter text")
    generated_at: str = Field(..., description="Generation timestamp")
    duration_ms: int = Field(..., description="Processing time in milliseconds")


class HealthResponse(BaseModel):
    status: str
    pipeline_ready: bool
    version: str
    timestamp: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


@app.middleware("http")
async def log_requests(request: Request, call_next):
    rid = str(uuid.uuid4())[:8]
    logger.info(f"[{rid}] {request.method} {request.url.path}")
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = int((time.perf_counter() - t0) * 1000)
    logger.info(f"[{rid}] → {response.status_code} ({ms}ms)")
    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.detail).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
        ).model_dump(),
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Check service health",
    tags=["System"],
)
async def health():
    return HealthResponse(
        status="ok" if pipeline is not None else "initializing",
        pipeline_ready=pipeline is not None,
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
    )


@app.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate an administrative letter",
    tags=["Letter"],
    responses={
        200: {"description": "Letter generated successfully"},
        422: {"description": "Invalid input"},
        503: {"description": "Service not ready"},
    },
)
async def generate_letter(body: GenerateRequest) -> GenerateResponse:
    if pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The pipeline is not ready yet. Please try again shortly.",
        )

    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] Generating letter — subject: {body.subject!r}")

    t0 = time.perf_counter()
    try:
        letter = pipeline.run(body.model_dump())
    except Exception as e:
        logger.exception(f"[{request_id}] Generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while generating the letter: {e}",
        ) from e

    duration_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(f"[{request_id}] Done in {duration_ms}ms")

    return GenerateResponse(
        request_id=request_id,
        letter=letter,
        generated_at=datetime.now().isoformat(),
        duration_ms=duration_ms,
    )


@app.get(
    "/examples",
    summary="Show available examples from the knowledge base",
    tags=["Letter"],
)
async def get_examples() -> Dict[str, Any]:
    return {
        "count": len(KnowledgeBase.EXAMPLES),
        "examples": [
            {
                "metadata": ex["metadata"],
                "preview": ex["text"][:120] + "...",
            }
            for ex in KnowledgeBase.EXAMPLES
        ],
    }


@app.get(
    "/",
    include_in_schema=False,
)
async def root():
    return {"message": "Dabirkhane API — visit /docs"}