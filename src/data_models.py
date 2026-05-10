from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

LengthOption = Literal["small", "medium", "big"]

LENGTH_RANGES: dict[LengthOption, tuple[int, int]] = {
    "small":  (80,  120),
    "medium": (150, 250),
    "big":    (300, 450),
}


class LetterRequest(BaseModel):
    from_role: Optional[str] = Field(
        default=None,
        description="نقش فرستنده: رئیس، مدیر، کارگر، کارمند، ..."
    )
    to_role: Optional[str] = Field(default=None, description="نقش گیرنده: رئیس، مدیر، کارگر، کارمند، ...")
    subject: str = Field(..., description="موضوع نامه")
    purpose: str = Field(..., description="هدف نامه")
    details: str = Field(..., description="جزئیات لازم برای تولید متن")
    tone: Optional[str] = Field(default=None, description="لحن اختیاری؛ اگر خالی باشد به‌صورت پیش‌فرض formal می‌شود")
    date: Optional[str] = Field(default=None, description="تاریخ نامه؛ اگر نباشد تاریخ امروز استفاده می‌شود")
    org_name: Optional[str] = Field(default=None, description="نام سازمان / شرکت")
    language: str = Field(default="fa", description="زبان خروجی")
    length: LengthOption = Field(
        default="medium",
        description="طول نامه: small (۸۰-۱۲۰ کلمه) | medium (۱۵۰-۲۵۰ کلمه) | big (۳۰۰-۴۵۰ کلمه)",
    )

    def effective_tone(self) -> str:
        return self.tone.strip() if self.tone and self.tone.strip() else "formal"

    def effective_date(self) -> str:
        return self.date.strip() if self.date and self.date.strip() \
            else datetime.now().strftime("%Y/%m/%d")

    def effective_length(self) -> str:
        lo, hi = LENGTH_RANGES[self.length]
        return f"{self.length} ({lo}–{hi} words)"


class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="آیا نامه قابل قبول است")
    score: int = Field(..., ge=0, le=10, description="امتیاز کیفیت ۰ تا ۱۰")
    issues: List[str] = Field(default_factory=list, description="فهرست اشکالات")
    rewrite_hint: str = Field(default="", description="راهنمای بازنویسی")


class LetterState(TypedDict, total=False):
    request: dict         
    tone: str
    style_hint: str
    retrieval_query: str
    retrieved_examples: str
    date: str
    draft: str
    validation: dict   
    revision_count: int
    final_letter: str
    history: str
