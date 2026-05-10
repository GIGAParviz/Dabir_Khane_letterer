from __future__ import annotations

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
