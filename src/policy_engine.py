from __future__ import annotations

from typing import Optional
from config import Config

class PolicyEngine:
    def __init__(self, config: Config = Config()):
        self.higher_roles = [r.lower() for r in config.HIGHER_ROLES]
        self.lower_roles  = [r.lower() for r in config.LOWER_ROLES]

    def _normalize(self, s: Optional[str]) -> str:
        return (s or "").strip().lower()

    def _is_higher(self, role: str) -> bool:
        return any(k in role for k in self.higher_roles)

    def _is_lower(self, role: str) -> bool:
        return any(k in role for k in self.lower_roles)

    def infer_tone(self, from_role: Optional[str], to_role: Optional[str],
                   base_tone: str) -> str:
        fr = self._normalize(from_role)
        tr = self._normalize(to_role)

        if not fr or not tr:
            return base_tone

        if self._is_higher(fr) and self._is_lower(tr):
            return "authoritative_formal"
        if self._is_lower(fr) and self._is_higher(tr):
            return "respectful_formal"
        return base_tone

    def infer_style_hint(self, from_role: Optional[str], to_role: Optional[str],
                          tone: str) -> str:
        fr = self._normalize(from_role)
        tr = self._normalize(to_role)

        if not fr or not tr:
            return f"{tone}, neutral, formal"

        if self._is_higher(fr) and self._is_lower(tr):
            return "authoritative formal, warning tone, firm but professional"
        if self._is_lower(fr) and self._is_higher(tr):
            return f"{tone}, very polite, deferential, respectful"
        return f"{tone}, neutral, formal"
