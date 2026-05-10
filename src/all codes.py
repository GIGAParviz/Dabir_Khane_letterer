#api.py
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
# ------------------------------------------------------------------------------------------------------------------
# config.py
# removed duplicate future import

from typing import List

class Config:
    OLLAMA_MODEL: str = "qwen3:8b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    LOCAL_LOAD: bool = True

    GENERATOR_TEMP: float = 0.4
    GENERATOR_MAX_TOKENS: int = 1500
    VALIDATOR_TEMP: float = 0.0
    VALIDATOR_MAX_TOKENS: int = 512

    CHROMA_COLLECTION: str = "letter_examples"
    CHROMA_PERSIST_DIR: str = "./letter_rag_db"
    RETRIEVAL_TOP_K: int = 3

    MIN_LETTER_LENGTH: int = 120
    MIN_SCORE: int = 7
    MAX_REVISIONS: int = 1

    HIGHER_ROLES: List[str] = [
        "رئیس", "مدیر", "سرپرست", "boss", "manager", "ceo", "supervisor"
    ]
    LOWER_ROLES: List[str] = [
        "کارگر", "کارمند", "staff", "employee", "worker", "assistant"
    ]

    LENGTH_RANGES: dict = {
        "small":  (80,  120),
        "medium": (150, 250),
        "big":    (300, 450),
    }

# ------------------------------------------------------------------------------------------------------------------
# data_models.py
# removed duplicate future import

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

LengthOption = Literal["small", "medium", "big"]

LENGTH_RANGES: dict[LengthOption, tuple[int, int]] = {
    "small":  (80,  120),
    "medium": (150, 250),
    "big":    (300, 450),
}


class LetterRequest(BaseModel):
    from_role: Optional[str] = Field(
        default=None,
        description="نقش فرستنده: رئیس، مدیر، کارگر، کارمند، ..."
    )
    to_role: Optional[str] = Field(default=None, description="نقش گیرنده: رئیس، مدیر، کارگر، کارمند، ...")
    subject: str = Field(..., description="موضوع نامه")
    purpose: str = Field(..., description="هدف نامه")
    details: str = Field(..., description="جزئیات لازم برای تولید متن")
    tone: Optional[str] = Field(default=None, description="لحن اختیاری؛ اگر خالی باشد به‌صورت پیش‌فرض formal می‌شود")
    date: Optional[str] = Field(default=None, description="تاریخ نامه؛ اگر نباشد تاریخ امروز استفاده می‌شود")
    org_name: Optional[str] = Field(default=None, description="نام سازمان / شرکت")
    language: str = Field(default="fa", description="زبان خروجی")
    length: LengthOption = Field(
        default="medium",
        description="طول نامه: small (۸۰-۱۲۰ کلمه) | medium (۱۵۰-۲۵۰ کلمه) | big (۳۰۰-۴۵۰ کلمه)",
    )

    def effective_tone(self) -> str:
        return self.tone.strip() if self.tone and self.tone.strip() else "formal"

    def effective_date(self) -> str:
        return self.date.strip() if self.date and self.date.strip() \
            else datetime.now().strftime("%Y/%m/%d")

    def effective_length(self) -> str:
        lo, hi = LENGTH_RANGES[self.length]
        return f"{self.length} ({lo}–{hi} words)"


class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="آیا نامه قابل قبول است")
    score: int = Field(..., ge=0, le=10, description="امتیاز کیفیت ۰ تا ۱۰")
    issues: List[str] = Field(default_factory=list, description="فهرست اشکالات")
    rewrite_hint: str = Field(default="", description="راهنمای بازنویسی")


class LetterState(TypedDict, total=False):
    request: dict         
    tone: str
    style_hint: str
    retrieval_query: str
    retrieved_examples: str
    date: str
    draft: str
    validation: dict   
    revision_count: int
    final_letter: str
    history: str

# ------------------------------------------------------------------------------------------------------------------
# embed_factor.py
# removed duplicate future import

from langchain_community.embeddings import HuggingFaceEmbeddings

class EmbeddingFactory:
    @staticmethod
    def create(model_name: str, local_only: bool = False) -> HuggingFaceEmbeddings:
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"local_files_only": local_only},
        )

# ------------------------------------------------------------------------------------------------------------------
# graphs.py
# removed duplicate future import

import json
import re
from langchain_huggingface import ChatHuggingFace
from config import Config
from data_models import LetterState, LetterRequest
from policy_engine import PolicyEngine
from rag_retriever import RAGRetriever
from prompt_library import PromptLibrary
from letter_validat import LetterValidator


class GraphNodes:
    def __init__(
        self,
        retriever:RAGRetriever,
        generator_llm: ChatHuggingFace,
        validator: LetterValidator,
        policy: PolicyEngine,
        config: Config = Config(),
    ):
        self.retriever = retriever
        self.generator_llm = generator_llm
        self.validator = validator
        self.policy = policy
        self.config = config

        self._gen_prompt = PromptLibrary.generator()
        self._rewrite_prompt = PromptLibrary.rewriter()

        self._gen_chain = self._gen_prompt | self.generator_llm
        self._rewrite_chain = self._rewrite_prompt | self.generator_llm


    def normalize_input(self, state: LetterState) -> dict:
        req = LetterRequest.model_validate(state["request"])
        tone = self.policy.infer_tone(req.from_role, req.to_role, req.effective_tone())
        style = self.policy.infer_style_hint(req.from_role, req.to_role, tone)
        date = req.effective_date()

        retrieval_query = self._build_retrieval_query(req, style)

        return {
            "request": req.model_dump(),
            "tone": tone,
            "style_hint": style,
            "date": date,
            "retrieval_query": retrieval_query,
        }

    def retrieve_examples(self, state: LetterState) -> dict:
        print("[Pipeline] Retrieving examples...")
        req  = LetterRequest.model_validate(state["request"])
        docs = self.retriever.retrieve(state["retrieval_query"], req)
        return {"retrieved_examples": RAGRetriever.format_docs(docs)}

    def generate_draft(self, state: LetterState) -> dict:
        print("[Pipeline] Generating draft...")
        req = LetterRequest.model_validate(state["request"])
        out = self._gen_chain.invoke({
            "request_json": self._format_request(req),
            "tone": state["tone"],
            "style_hint": state["style_hint"],
            "date": state["date"],
            "length": req.effective_length(),
            "retrieved_examples": state["retrieved_examples"],
        })
        return {"draft": self._clean(out.content)}

    def validate_draft(self, state: LetterState) -> dict:
        print("[Pipeline] Validating draft...")
        req = LetterRequest.model_validate(state["request"])
        result = self.validator.validate(state["draft"], req)
        return {"validation": result.model_dump()}


    def rewrite_draft(self, state: LetterState) -> dict:
        print("[Pipeline] Rewriting draft...")
        req = LetterRequest.model_validate(state["request"])
        out = self._rewrite_chain.invoke({
            "request_json": self._format_request(req),
            "tone": state["tone"],
            "style_hint": state["style_hint"],
            "date": state["date"],
            "length": req.effective_length(),
            "retrieved_examples": state["retrieved_examples"],
            "draft": state.get("draft", ""),
            "validation_json": json.dumps(
                                    state.get("validation", {}),
                                    ensure_ascii=False,
                                    indent=2
                                 ),
            "history": state.get("history", ""),
        })
        return {
            "draft": self._clean(out.content),
            "revision_count": state.get("revision_count", 0) + 1,
        }
    def finalize(self, state: LetterState) -> dict:
        return {"final_letter": self._clean(state["draft"])}

    def should_rewrite(self, state: LetterState) -> str:
        validation = state["validation"]
        revision_count = state.get("revision_count", 0)

        if validation["is_valid"]:
            return "finalize"
        if revision_count < self.config.MAX_REVISIONS:
            return "rewrite_draft"
        return "finalize"

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    @staticmethod
    def _format_request(req: LetterRequest) -> str:
        return json.dumps(req.model_dump(), ensure_ascii=False, indent=2)

    @staticmethod
    def _build_retrieval_query(req: LetterRequest, style_hint: str) -> str:
        parts = [
            f"نقش فرستنده: {req.from_role or ''}",
            f"نقش گیرنده: {req.to_role or ''}",
            f"موضوع: {req.subject}",
            f"هدف: {req.purpose}",
            f"جزئیات: {req.details}",
            f"لحن: {style_hint}",
            f"سازمان: {req.org_name or ''}",
        ]
        return " | ".join(p for p in parts if p.strip().split(": ", 1)[-1])

# ------------------------------------------------------------------------------------------------------------------
# knowledge_base.py
# removed duplicate future import

from typing import Any, Dict, List
from langchain_core.documents import Document


class KnowledgeBase:
    EXAMPLES: List[Dict[str, Any]] = [
        {
            "text": (
                "تاریخ: ۱۴۰۳/۱۰/۰۷\n"
                "شماره: ۲۵۹۱\n\n"
                "ریاست محترم هیئت مدیره\n"
                "شرکت نمونه\n\n"
                "با سلام و احترام،\n\n"
                "احتراماً، به استحضار می‌رساند گزارش عملکرد واحد فناوری اطلاعات "
                "در سه‌ماهه سوم سال جاری به شرح زیر تقدیم می‌گردد:\n\n"
                "در این دوره، تمرکز اصلی واحد بر بهبود زیرساخت‌های نرم‌افزاری و "
                "افزایش امنیت سامانه‌ها بوده است. پروژه ارتقاء سیستم مدیریت داده‌ها "
                "با موفقیت به پایان رسید و منجر به کاهش ۳۰ درصدی خطاهای سیستمی گردید.\n\n"
                "همچنین اقدامات لازم در جهت بهینه‌سازی فرآیند پشتیبانی انجام شد "
                "که نتیجه آن کاهش زمان پاسخگویی از ۴۸ ساعت به کمتر از ۲۴ ساعت بوده است.\n\n"
                "با تقدیم احترام\n"
                "مدیر فناوری اطلاعات"
            ),
            "metadata": {
                "from_role": "مدیر",
                "to_role": "هیئت مدیره",
                "type": "report",
                "tone": "formal"
            }
        },
        {
            "text": (
                "تاریخ: ۱۴۰۳/۱۰/۰۶\n"
                "شماره: ۲۵۹۰\n\n"
                "جناب آقای احمدی\n"
                "سرپرست محترم واحد تولید\n\n"
                "با سلام و احترام،\n\n"
                "با عنایت به گزارش‌های دریافتی در خصوص تأخیرهای مکرر در ارسال "
                "گزارش‌های روزانه، به استحضار می‌رساند این موضوع موجب اختلال در "
                "روند برنامه‌ریزی سازمان شده است.\n\n"
                "لذا مقتضی است دستور فرمایید ضمن بررسی دقیق علل، اقدامات لازم جهت "
                "جلوگیری از تکرار آن در اسرع وقت به عمل آید.\n\n"
                "بدیهی است در صورت تداوم این روند، ناگزیر به اتخاذ تصمیمات مقتضی "
                "اداری خواهیم بود.\n\n"
                "با تشکر\n"
                "مدیر عملیات"
            ),
            "metadata": {
                "from_role": "مدیر",
                "to_role": "سرپرست",
                "type": "warning",
                "tone": "authoritative_formal"
            }
        },
        {
            "text": (
                "تاریخ: ۱۴۰۳/۱۰/۰۵\n"
                "شماره: ۲۵۸۹\n\n"
                "مدیریت محترم منابع انسانی\n"
                "شرکت توسعه فناوری\n\n"
                "با سلام و احترام،\n\n"
                "احتراماً، اینجانب به عنوان کارمند واحد فنی، به استحضار می‌رساند "
                "با توجه به افزایش حجم پروژه‌های محوله، نیاز به تقویت نیروی انسانی "
                "در این بخش بیش از پیش احساس می‌شود.\n\n"
                "لذا خواهشمند است دستور فرمایید ضمن بررسی شرایط موجود، نسبت به "
                "جذب نیروی متخصص اقدام لازم صورت پذیرد.\n\n"
                "پیشاپیش از توجه و همکاری حضرت‌عالی کمال تشکر را دارم.\n\n"
                "با احترام\n"
                "کارشناس واحد فنی"
            ),
            "metadata": {
                "from_role": "کارمند",
                "to_role": "مدیر",
                "type": "request",
                "tone": "respectful_formal"
            }
        },
        {
            "text": (
                "تاریخ: ۱۴۰۳/۰۸/۱۵\n"
                "شماره: ۱۰۲۳۴\n\n"
                "با سلام و احترام،\n\n"
                "بدین‌وسیله به اطلاع می‌رساند گزارش عملکرد ماهانه می‌بایست "
                "حداکثر تا پایان هر ماه به واحد مربوطه ارسال گردد. خواهشمند است "
                "دستور فرمایید اقدامات لازم در این خصوص انجام شود.\n\n"
                "با تشکر\n"
                "مدیریت شرکت نمونه"
            ),
            "metadata": {
                "from_role": "مدیر",
                "to_role": "کارمند",
                "type": "instruction",
                "tone": "formal"
            }
        },
        {
            "text": (
                "تاریخ: ۱۴۰۳/۰۸/۱۶\n"
                "شماره: ۱۰۲۳۵\n\n"
                "با سلام و احترام،\n\n"
                "احتراماً خواهشمند است دستور فرمایید درخواست مرخصی اینجانب "
                "مورد بررسی قرار گیرد. پیشاپیش از همکاری شما سپاسگزارم.\n\n"
                "با احترام\n"
                "کارمند بخش اداری"
            ),
            "metadata": {
                "from_role": "کارمند",
                "to_role": "مدیر",
                "type": "request",
                "tone": "respectful_formal"
            }
        },
        {
            "text": (
                "تاریخ: ۱۴۰۳/۰۸/۱۷\n"
                "شماره: ۱۰۲۳۶\n\n"
                "با سلام و احترام،\n\n"
                "با توجه به اهمیت نظم در فرآیند اجرایی، لازم است کلیه گزارش‌ها "
                "در موعد مقرر ارسال گردد. هرگونه تأخیر موجب اختلال در روند "
                "تصمیم‌گیری خواهد شد.\n\n"
                "با تشکر\n"
                "رئیس واحد"
            ),
            "metadata": {
                "from_role": "رئیس",
                "to_role": "کارگر",
                "type": "warning",
                "tone": "authoritative_formal"
            }
        },
    ]

    @classmethod
    def get_documents(cls) -> List[Document]:
        return [
            Document(page_content=item["text"], metadata=item["metadata"])
            for item in cls.EXAMPLES
        ]


# ------------------------------------------------------------------------------------------------------------------
#letter_validat.py
# removed duplicate future import

import re
import json
from typing import List

from langchain_ollama import ChatOllama
from data_models import LetterRequest, ValidationResult
from config import Config
from prompt_library import PromptLibrary


class LetterValidator:
    INFORMAL_PATTERNS = [r"داداش", r"عزیزم", r"مرسی", r"دمت گرم", r"خوبی؟"]
    MODEL_LEAK_PATTERNS = ["here is", "sure", "of course", "analysis", "reasoning",
                           "certainly", "as an ai"]

    def __init__(self, llm: ChatOllama, config: Config = Config()):
        self.llm = llm
        self.config = config
        self._prompt = PromptLibrary.validator()
        self._chain = self._prompt | self.llm

    def rule_check(self, draft: str, req: LetterRequest) -> List[str]:
        issues: List[str] = []

        if len(draft.strip()) < self.config.MIN_LETTER_LENGTH:
            issues.append("متن بیش از حد کوتاه است.")

        greetings = ["با سلام و احترام", "سلام و احترام", "با سلام"]
        if not any(g in draft for g in greetings):
            issues.append("بخش آغازین/تحیت رسمی ندارد.")

        closings = ["با تشکر", "با سپاس", "ارادتمند", "با احترام"]
        if not any(c in draft for c in closings):
            issues.append("بخش پایانی/خاتمه رسمی ندارد.")

        if req.effective_tone() in ("formal", "authoritative_formal", "respectful_formal"):
            if any(re.search(p, draft) for p in self.INFORMAL_PATTERNS):
                issues.append("واژگان غیررسمی دیده شد.")

        if any(p in draft.lower() for p in self.MODEL_LEAK_PATTERNS):
            issues.append("متن شبیه خروجی توضیحی مدل است، نه نامه نهایی.")

        return issues


    def llm_check(self, draft: str, req: LetterRequest) -> ValidationResult:
        try:
            response = self._chain.invoke({
                "request_json": self._format_request(req),
                "draft": draft,
            })
            return self._parse_response(response.content)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                score=0,
                issues=[f"خطا در اعتبارسنجی LLM: {e}"],
                rewrite_hint="لطفاً فرمت JSON را بررسی کنید."
            )


    def validate(self, draft: str, req: LetterRequest) -> ValidationResult:
        rule_issues  = self.rule_check(draft, req)
        llm_result   = self.llm_check(draft, req)

        combined_issues = list(dict.fromkeys(rule_issues + llm_result.issues))
        is_valid = (
            llm_result.is_valid
            and len(rule_issues) == 0
            and llm_result.score >= self.config.MIN_SCORE
        )

        return ValidationResult(
            is_valid=is_valid,
            score=llm_result.score,
            issues=combined_issues,
            rewrite_hint=llm_result.rewrite_hint,
        )


    @staticmethod
    def _format_request(req: LetterRequest) -> str:
        return json.dumps(req.model_dump(), ensure_ascii=False, indent=2)

    @staticmethod
    def _parse_response(text: str) -> ValidationResult:
        try:
            clean = re.sub(r"```(?:json)?|```", "", text).strip()
            data  = json.loads(clean)
            return ValidationResult(**data)
        except Exception:
            return ValidationResult(
                is_valid=False,
                score=0,
                issues=["خروجی JSON نامعتبر از مدل"],
                rewrite_hint="فرمت JSON دقیق باید رعایت شود."
            )

# ------------------------------------------------------------------------------------------------------------------
#llm_factor.py
# removed duplicate future import

from langchain_ollama import ChatOllama
from config import Config


class LLMFactory:
    def __init__(self, config: Config = Config()):
        self.config = config

    def create(self, temperature: float, max_new_tokens: int) -> ChatOllama:
        return ChatOllama(
            model=self.config.OLLAMA_MODEL,
            base_url=self.config.OLLAMA_BASE_URL,
            temperature=temperature,
            num_predict=max_new_tokens,
        )

    def generator(self) -> ChatOllama:
        return self.create(self.config.GENERATOR_TEMP, self.config.GENERATOR_MAX_TOKENS)

    def validator(self) -> ChatOllama:
        return self.create(self.config.VALIDATOR_TEMP, self.config.VALIDATOR_MAX_TOKENS)
# ------------------------------------------------------------------------------------------------------------------
#pip_liner.py
# removed duplicate future import

from langgraph.graph import START, END, StateGraph
from config import Config
from data_models import LetterState
from policy_engine import PolicyEngine
from knowledge_base import KnowledgeBase
from rag_retriever import RAGRetriever
from llm_factory import LLMFactory
from letter_validat import LetterValidator
from graphs import GraphNodes

class LetterGenerationPipeline:
    def __init__(self, config: Config = Config()):
        self.config = config
        self._graph = None
        self._build()

    def _build(self) -> None:
        llm_factory = LLMFactory(self.config)
        gen_llm = llm_factory.generator()
        val_llm = llm_factory.validator()

        retriever = RAGRetriever(self.config).build(KnowledgeBase.get_documents())
        policy = PolicyEngine(self.config)
        validator = LetterValidator(val_llm, self.config)
        nodes = GraphNodes(retriever, gen_llm, validator, policy, self.config)

        builder = StateGraph(LetterState)

        builder.add_node("normalize_input", nodes.normalize_input)
        builder.add_node("retrieve_examples", nodes.retrieve_examples)
        builder.add_node("generate_draft", nodes.generate_draft)
        builder.add_node("validate_draft", nodes.validate_draft)
        builder.add_node("rewrite_draft", nodes.rewrite_draft)
        builder.add_node("finalize", nodes.finalize)

        builder.add_edge(START, "normalize_input")
        builder.add_edge("normalize_input", "retrieve_examples")
        builder.add_edge("retrieve_examples", "generate_draft")
        builder.add_edge("generate_draft",    "validate_draft")

        builder.add_conditional_edges(
            "validate_draft",
            nodes.should_rewrite,
            {
                "rewrite_draft": "rewrite_draft",
                "finalize": "finalize",
            }
        )

        builder.add_edge("rewrite_draft", "validate_draft")
        builder.add_edge("finalize", END)

        self._graph = builder.compile()
        print("[Pipeline] Graph compiled successfully.")

    def run(self, request: dict) -> str:
        initial_state: LetterState = {
            "request":        request,
            "revision_count": 0,
            "history":        "",
        }
        result = self._graph.invoke(initial_state)
        return result.get("final_letter", "")
# ------------------------------------------------------------------------------------------------------------------
#policy_engine.py
# removed duplicate future import

from typing import Optional
from config import Config

class PolicyEngine:
    def __init__(self, config: Config = Config()):
        self.higher_roles = [r.lower() for r in config.HIGHER_ROLES]
        self.lower_roles  = [r.lower() for r in config.LOWER_ROLES]

    def _normalize(self, s: Optional[str]) -> str:
        return (s or "").strip().lower()

    def _is_higher(self, role: str) -> bool:
        return any(k in role for k in self.higher_roles)

    def _is_lower(self, role: str) -> bool:
        return any(k in role for k in self.lower_roles)

    def infer_tone(self, from_role: Optional[str], to_role: Optional[str],
                   base_tone: str) -> str:
        fr = self._normalize(from_role)
        tr = self._normalize(to_role)

        if not fr or not tr:
            return base_tone

        if self._is_higher(fr) and self._is_lower(tr):
            return "authoritative_formal"
        if self._is_lower(fr) and self._is_higher(tr):
            return "respectful_formal"
        return base_tone

    def infer_style_hint(self, from_role: Optional[str], to_role: Optional[str],
                          tone: str) -> str:
        fr = self._normalize(from_role)
        tr = self._normalize(to_role)

        if not fr or not tr:
            return f"{tone}, neutral, formal"

        if self._is_higher(fr) and self._is_lower(tr):
            return "authoritative formal, warning tone, firm but professional"
        if self._is_lower(fr) and self._is_higher(tr):
            return f"{tone}, very polite, deferential, respectful"
        return f"{tone}, neutral, formal"

# ------------------------------------------------------------------------------------------------------------------
#prompt_library.py
# removed duplicate future import

from langchain_core.prompts import ChatPromptTemplate

class PromptLibrary:
    @staticmethod
    def generator() -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert Persian administrative letter writer. "
                "Write ONLY the final letter. Do NOT add any explanation, "
                "labels, commentary, or reasoning. "
                "Use formal Persian. Keep the structure natural and office-appropriate."
            ),
            (
                "human",
                """Request JSON:
                {request_json}
                
                Tone: {tone}
                Style hint: {style_hint}
                Date: {date}
                Target length: {length}

                Retrieved examples (for structure inspiration — do NOT copy):
                {retrieved_examples}

                Rules:
                - Always include the date at the top in formal Persian format
                - Output ONLY the letter — no preamble, no explanation
                - STRICTLY follow the target length — count your words and stay within the given range
                - At least 3 paragraphs:
                  1. Introduction of subject
                  2. Explanation / body
                  3. Request / conclusion
                - Formal greeting (با سلام و احترام) and formal closing (با تشکر / با احترام)
                - Do NOT use informal words or model-like explanatory language
                """
                ),
            ])

    @staticmethod
    def rewriter() -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                "You are revising a Persian administrative letter. "
                "Fix all reported issues without changing the core meaning. "
                "Return ONLY the revised letter text."
            ),
            (
                "human",
                """Original request:
                {request_json}

                Length: {length}
                Tone: {tone}
                Style hint: {style_hint}
                Date: {date}

                Relevant examples:
                {retrieved_examples}

                Previous draft:
                {draft}

                Validation feedback:
                {validation_json}

                Conversation history:
                {history}

                Rewrite so it is fully formal, complete, and aligned with the request.
                STRICTLY respect the target length — adjust content to fit within the given word range.
                Return ONLY the letter no Json.
                """
            ),
        ])

    @staticmethod
    def validator() -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a strict reviewer of Persian administrative letters. "
                "Return ONLY valid JSON. No explanation, no markdown fences."
            ),
            (
                "human",
                """Request JSON:
                {request_json}

                Draft letter:
                {draft}

                Return ONLY JSON in this exact format:
                {{
                  "is_valid": true,
                  "score": 8,
                  "issues": [],
                  "rewrite_hint": ""
                }}

                Checklist:
                - Correct tone (formal/authoritative/respectful as required)
                - Formal Persian language
                - Office-appropriate structure
                - Proper greeting and closing
                - Minimum 3 paragraphs
                """
            ),
        ])

# ------------------------------------------------------------------------------------------------------------------
# rag_retriever.py
 
# removed duplicate future import

from reranker import Reranker
from config import Config
from embed_factory import EmbeddingFactory
from langchain_community.vectorstores import Chroma
from typing import List, Optional
from langchain_core.documents import Document
from data_models import LetterRequest
import json



class RAGRetriever:
    def __init__(self, config: Config = Config()):
        self.config   = config
        self.reranker = Reranker()
        self._store: Optional[Chroma] = None

    def build(self, documents: List[Document]) -> "RAGRetriever":
        embeddings = EmbeddingFactory.create(self.config.EMBEDDING_MODEL, self.config.LOCAL_LOAD)
        self._store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            collection_name=self.config.CHROMA_COLLECTION,
            persist_directory=self.config.CHROMA_PERSIST_DIR,
        )
        return self

    def retrieve(self, query: str, req: LetterRequest) -> List[Document]:
        if self._store is None:
            raise RuntimeError("no Build maded, call vectorstore first")
        filter_query = self._build_filter(req)

        docs = self._store.similarity_search(
            query=query,
            k=self.config.RETRIEVAL_TOP_K,
            filter=filter_query,
        )

        if not docs:
            docs = self._store.similarity_search(query, k=self.config.RETRIEVAL_TOP_K)

        return self.reranker.rerank(docs, req)

    @staticmethod
    def _build_filter(req: LetterRequest) -> Optional[dict]:
        conditions = []
        if req.from_role:
            conditions.append({"from_role": {"$eq": req.from_role}})
        if req.to_role:
            conditions.append({"to_role": {"$eq": req.to_role}})

        if len(conditions) == 0:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    @staticmethod
    def format_docs(docs: List[Document]) -> str:
        if not docs:
            return "No examples retrieved."
        blocks = []
        for i, d in enumerate(docs, start=1):
            blocks.append(
                f"### Example {i}\n"
                f"Metadata: {json.dumps(d.metadata, ensure_ascii=False)}\n"
                f"Text:\n{d.page_content}"
            )
        return "\n\n".join(blocks)
# ------------------------------------------------------------------------------------------------------------------
# reranker.py
# removed duplicate future import

from typing import List, Tuple
from data_models import LetterRequest
from langchain_core.documents import Document

class Reranker:
    def rerank(self, docs: List[Document], req: LetterRequest) -> List[Document]:
        scored: List[Tuple[float, Document]] = []
        for doc in docs:
            score = self._score(doc, req)
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored]

    def _score(self, doc: Document, req: LetterRequest) -> float:
        meta = doc.metadata
        score = 0.0
        if req.from_role and meta.get("from_role") == req.from_role:
            score += 1.0
        if req.to_role and meta.get("to_role") == req.to_role:
            score += 1.0
        tone = req.effective_tone()
        if meta.get("tone") and tone in meta["tone"]:
            score += 0.5
        return score
