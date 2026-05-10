from __future__ import annotations

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