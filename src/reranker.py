from __future__ import annotations

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
