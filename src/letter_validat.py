from __future__ import annotations

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
