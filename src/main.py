from __future__ import annotations

from config import Config
from pipe_liner import LetterGenerationPipeline

if __name__ == "__main__":
    sample_request = {
        "from_role":  "کارمند",
        "to_role": "مدیر",
        "subject": "درخواست صندلی اضافه برای دفتر",
        "purpose": "ارائه درخواست رسمی برای خرید ۵ عدد صندلی برای اتاق کنفرانس",
        "date": "1404/02/24",
        "details": ("اتاق کنفرانس در مواقع جلسه بسیار شلوغ میشه و اصلا نمیتونیم جلسه به درستی برگزار کنیم"),
        # "tone": "respectful_formal",   
        "org_name":   "شرکت نمونه",
        "length": "small",
        "language":   "fa",
    }

    pipeline = LetterGenerationPipeline(Config())
    letter = pipeline.run(sample_request)

    print("\n" + "=" * 60)
    print("               نامه نهایی")
    print("=" * 60)
    print(letter)
    print("=" * 60)
