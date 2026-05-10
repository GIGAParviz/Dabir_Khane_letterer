# ══════════════════════════════════════════════════════
# Stage 1 — Builder
# ══════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ══════════════════════════════════════════════════════
# Stage 2 — Runtime
# ══════════════════════════════════════════════════════
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /install /usr/local

COPY api.py            .
COPY config.py         .
COPY data_models.py    .
COPY embed_factory.py  .
COPY graphs.py         .
COPY knowledge_base.py .
COPY letter_validat.py .
COPY llm_factory.py    .
COPY pipe_liner.py     .
COPY policy_engine.py  .
COPY prompt_library.py .
COPY rag_retriever.py  .
COPY reranker.py       .

RUN mkdir -p /app/letter_rag_db \
    && chown -R appuser:appuser /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]