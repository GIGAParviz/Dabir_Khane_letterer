from __future__ import annotations

# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

class EmbeddingFactory:
    @staticmethod
    def create(model_name: str, local_only: bool = False) -> HuggingFaceEmbeddings:
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"local_files_only": local_only},
        )
