from __future__ import annotations
import os

from typing import List

class Config:
    OLLAMA_MODEL = "qwen3:8b"

    # OLLAMA_BASE_URL = "http://host.docker.internal:11434"    
    OLLAMA_BASE_URL = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
        )
    
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