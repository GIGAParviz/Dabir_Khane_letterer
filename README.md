<<<<<<< HEAD
# Dabirkhane

> An intelligent API for generating Persian administrative letters with retrieval-augmented generation (RAG), LangGraph orchestration, and Hugging Face-hosted language models.

## Overview

Dabirkhane is a FastAPI-based service that generates formal administrative letters from structured request data. The system combines:

- **Policy-based tone inference** for role-aware writing style
- **RAG retrieval** from a curated set of example letters
- **LLM generation** for first-pass draft creation
- **LLM + rule-based validation** for quality control
- **Automatic rewriting** when the draft does not meet quality thresholds

The current codebase is oriented around Persian administrative correspondence, but the API layer also exposes an English-facing request schema. The implementation currently uses a fixed Hugging Face model configuration in `config.py` and loads example letters from `knowledge_base.py`. 

## Key Features

- **FastAPI service** with `/health`, `/generate`, and `/examples` endpoints
- **LangGraph pipeline** for deterministic orchestration of generation steps
- **RAG-based context retrieval** using Chroma + embeddings
- **Role-aware tone inference** for sender/recipient combinations
- **Draft validation** with both rules and an LLM reviewer
- **Rewrite loop** for low-quality outputs, capped by `MAX_REVISIONS`
- **Structured API responses** with request IDs and duration metrics
- **CORS enabled** for browser-based integration
- **Clean error handling** with unified JSON errors

## Architecture Summary

The request flow is:

1. **API receives a letter request**
2. **Input is normalized**
   - request model validation
   - tone inference
   - style hint selection
   - retrieval query construction
3. **Relevant examples are retrieved**
   - Chroma similarity search
   - optional metadata filtering by sender/recipient role
   - reranking by role/tone match
4. **Draft is generated**
   - prompt includes request JSON, tone, style hint, date, and retrieved examples
5. **Draft is validated**
   - rule-based checks
   - LLM-based JSON review
6. **Rewrite loop**
   - if invalid and revision budget remains, the draft is rewritten
7. **Final response is returned**
   - final letter text
   - request ID
   - timestamp
   - latency in milliseconds

See `docs/ARCHITECTURE.md` for a deeper breakdown. 

## Installation

### Prerequisites

- Python 3.10+
- Access to Hugging Face models
- A valid Hugging Face API token
- A writable path for the Chroma persistence directory

### Setup

```bash
git clone <your-repo-url>
cd <your-repo-folder>

python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

pip install -U pip
pip install fastapi uvicorn langgraph langchain langchain-core langchain-community langchain-huggingface chromadb pydantic huggingface_hub
```

### Run the API

```bash
uvicorn api:app --reload
```

Then open:

- API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## Configuration

Configuration is centralized in `config.py`. The current code sets model and pipeline defaults directly in the `Config` class, including the Hugging Face model name, embedding model, retrieval settings, and validation thresholds. 

See `docs/CONFIGURATION.md` for the full reference table.

## Usage Examples

### Health check

```bash
curl http://127.0.0.1:8000/health
```

### List example letters

```bash
curl http://127.0.0.1:8000/examples
```

### Generate a letter

```bash
curl -X POST http://127.0.0.1:8000/generate   -H "Content-Type: application/json"   -d '{
    "from_role": "کارمند",
    "to_role": "مدیر",
    "subject": "درخواست مرخصی",
    "purpose": "ثبت درخواست مرخصی سالانه",
    "details": "با توجه به شرایط خانوادگی و برنامه‌ریزی قبلی، درخواست می‌کنم مرخصی سالانه من برای این بازه بررسی و تایید شود.",
    "tone": "respectful_formal",
    "date": "2025/05/14",
    "org_name": "شرکت نمونه",
    "language": "fa",
    "length": "medium"
  }'
```

### Python client example

```python
import requests

payload = {
    "from_role": "کارمند",
    "to_role": "مدیر",
    "subject": "درخواست مرخصی",
    "purpose": "ثبت درخواست مرخصی سالانه",
    "details": "با توجه به شرایط خانوادگی و برنامه‌ریزی قبلی، درخواست می‌کنم مرخصی سالانه من برای این بازه بررسی و تایید شود.",
    "tone": "respectful_formal",
    "language": "fa",
    "length": "medium",
}

response = requests.post("http://127.0.0.1:8000/generate", json=payload, timeout=60)
response.raise_for_status()
print(response.json()["letter"])
```

## Folder Structure

```text
.
├── api.py
├── config.py
├── data_models.py
├── embed_factor.py
├── graphs.py
├── knowledge_base.py
├── letter_validat.py
├── llm_factor.py
├── pip_liner.py
├── policy_engine.py
├── prompt_library.py
├── rag_retriever.py
├── reranker.py
└── docs/
    ├── ARCHITECTURE.md
    ├── CONFIGURATION.md
    └── CONTRIBUTING.md
```

## Error Handling and Troubleshooting

### Common issues

**1. Pipeline is not ready**
- Symptom: `503 Service Unavailable`
- Cause: the LangGraph pipeline has not finished initialization
- Action: retry the request shortly after startup

**2. Hugging Face token errors**
- Symptom: startup failure or model download/authentication errors
- Cause: invalid or missing Hugging Face credentials
- Action: verify the token and model access

**3. Chroma persistence errors**
- Symptom: retrieval failures or write permission errors
- Cause: the persistence directory is not writable
- Action: ensure `CHROMA_PERSIST_DIR` exists and is writable

**4. Validation rejects the draft**
- Symptom: the generated letter returns low quality or triggers rewrite
- Cause: missing greeting/closing, short output, informal wording, or JSON validation failure
- Action: increase input specificity and/or adjust prompt and validation thresholds

**5. Model output contains extra reasoning**
- Symptom: the output includes explanations instead of a clean letter
- Cause: the generator did not fully follow the prompt
- Action: tighten prompts or adjust post-processing and validation

The API also returns unified JSON errors from custom exception handlers, including a general `500` response with an error detail field. 

## Testing

No automated test suite was included in the provided source snapshot. That means the commands below are recommended project conventions rather than confirmed existing scripts.

### Recommended test layers

- **Unit tests** for:
  - tone inference in `PolicyEngine`
  - rule checks in `LetterValidator`
  - retrieval filters in `RAGRetriever`
  - request validation in the FastAPI models
- **Integration tests** for:
  - `/health`
  - `/examples`
  - `/generate`
- **Contract tests** for:
  - response schema stability
  - JSON error payloads
- **Smoke tests** for:
  - pipeline startup
  - model availability
  - Chroma persistence

### Example commands

```bash
pytest
pytest -q
```

## Deployment

### Local development

```bash
uvicorn api:app --reload
```

### Production pattern

Use a process manager or container runtime with one app process per worker, for example:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

For production deployments, place secrets in environment variables, mount a persistent volume for Chroma, and ensure outbound access to Hugging Face if the model is not cached locally.

### Suggested operational checks

- Health endpoint returns `status=ok`
- Model endpoint can authenticate successfully
- Chroma storage path is writable
- Logs show successful pipeline compilation on startup

## Contributing

See `docs/CONTRIBUTING.md` for the recommended workflow.

## Roadmap

Planned improvements for a mature release typically include:

- Move secrets out of source code and into environment variables
- Add a `.env.example` file
- Add automated tests and CI
- Add structured logging and request tracing
- Add more example letters and better retrieval metadata
- Support language-specific formatting rules
- Add pagination or search for examples
- Expose a streaming generation option
- Add Docker and deployment manifests

## License

No license file was included in the provided source snapshot. Add a license before public release. Common choices are:

- MIT
- Apache 2.0
- GPLv3

## Notes

This documentation is based on the provided source files and may contain explicit assumptions where the repository did not include deployment scripts, tests, or packaging metadata.
=======
# Dabir_Khane_letterer
>>>>>>> f0087b8b020301b4277675ccab3036b0a930838b
