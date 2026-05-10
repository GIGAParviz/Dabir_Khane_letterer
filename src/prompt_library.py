from __future__ import annotations

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

