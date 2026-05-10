from __future__ import annotations

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