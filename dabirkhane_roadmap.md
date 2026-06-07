# Roadmap دبیرخانه هوشمند — ۳ ماه
**مدل‌ها:** Dorna2:Q2_K_M (V-OCR) | qwen3:8b (استنتاج)  
**Deadline:** ۳ ماه | MVP: پایان ماه اول

---

## خلاصه اجرایی

| ماه | هدف | خروجی اصلی |
|-----|-----|------------|
| ماه ۱ | MVP | Pipeline کامل: آپلود → OCR → متادیتا → ثبت + UI ساده |
| ماه ۲ | Agentic | عامل‌های هوشمند + ارجاع + پیش‌نویس + Dashboard |
| ماه ۳ | Production | Fine-tuning + امنیت + deployment + QA |

---

## ماه اول — MVP (Days 1–30)

> **هدف:** pipeline کامل قابل نمایش: آپلود سند → V-OCR → استخراج متادیتا → طبقه‌بندی → ثبت + رابط کاربری ساده

---

### هفته ۱ (Days 1–7): زیرساخت + مدل‌ها

---

**T1.1 — Dev Environment Setup**
- **مدت:** ۳ روز
- **Research پیش‌نیاز:** ندارد
- **تکنولوژی:** Docker 24+, Python 3.11, PostgreSQL 15, Redis 7, Git, docker-compose
- **ورودی:** دسترسی سرور / لپ‌تاپ
- **خروجی:** `docker-compose.yml` اجراشده + همه سرویس‌های پایه در حال اجرا
- **وابستگی:** هیچ
- **نود دیاگرام:** FastAPI Gateway, Document DB, LongTermMemory

---

**T1.2 — Ollama + Dorna2 + qwen3:8b Setup**
- **مدت:** ۲ روز اجرا + ۱ روز Research
- **Research:** بنچمارک هر دو مدل، تست prompt فارسی، اندازه‌گیری latency و RAM مصرفی
- **تکنولوژی:** Ollama, Dorna2:Q2_K_M, qwen3:8b, CUDA/ROCm driver
- **ورودی:** GPU server با حداقل ۱۶ GB VRAM
- **خروجی:** هر دو مدل از طریق Ollama API پاسخ می‌دهند + نتایج بنچمارک
- **وابستگی:** T1.1
- **نود دیاگرام:** model_dorna, model_qwen

---

**T1.3 — FastAPI Scaffold**
- **مدت:** ۲ روز
- **Research پیش‌نیاز:** ندارد
- **تکنولوژی:** FastAPI, Pydantic v2, uvicorn, pytest, python-jose (JWT)
- **ورودی:** طراحی API spec اولیه
- **خروجی:** endpoint‌های `/health`, `/upload`, `/documents`, `/query` کار می‌کنند
- **وابستگی:** T1.1
- **نود دیاگرام:** FastAPI Gateway

---

### هفته ۲ (Days 8–14): V-OCR + پردازش سند

---

**T1.4 — V-OCR Integration (ماژول اصلی)**
- **مدت:** ۳ روز اجرا + ۱ روز Research
- **Research:** آزمایش Dorna2 برای OCR فارسی، طراحی prompt بهینه، مقایسه با tesseract
- **تکنولوژی:** Dorna2:Q2_K_M via Ollama, PyMuPDF, pdf2image, Pillow, python-magic
- **ورودی:** مجموعه PDF/تصویر اسکن‌شده نمونه فارسی
- **خروجی:** کلاس `OCRTool` — ورودی: `file_path` → خروجی: `str` (متن Unicode فارسی)
- **وابستگی:** T1.2
- **نود دیاگرام:** V-OCR Module

---

**T1.5 — Document Parser**
- **مدت:** ۲ روز
- **Research پیش‌نیاز:** ندارد
- **تکنولوژی:** hazm (نرمال‌ساز فارسی), PyMuPDF, python-docx, LangChain RecursiveCharacterTextSplitter
- **ورودی:** متن خام از V-OCR یا DOCX/TXT مستقیم
- **خروجی:** لیست chunk‌های تمیز و نرمال‌شده فارسی با metadata هر chunk
- **وابستگی:** T1.4
- **نود دیاگرام:** Document Parser

---

**T1.6 — MetadataExtractor**
- **مدت:** ۲ روز
- **Research پیش‌نیاز:** ۰.۵ روز (طراحی few-shot examples فارسی)
- **تکنولوژی:** qwen3:8b via Ollama, few-shot prompting, Pydantic validation
- **ورودی:** متن نامه (string)
- **خروجی:** `dict` — `{sender, receiver, date_shamsi, letter_number, subject}`
- **وابستگی:** T1.2, T1.5
- **نود دیاگرام:** MetadataExtractor

---

### هفته ۳ (Days 15–21): Pipeline هوشمند

---

**T1.7 — Classifier**
- **مدت:** ۳ روز
- **Research پیش‌نیاز:** ۰.۵ روز (تعریف taxonomy موضوعات سازمان)
- **تکنولوژی:** qwen3:8b, few-shot + zero-shot prompts, Pydantic
- **ورودی:** متن نامه
- **خروجی:** `dict` — `{topic, urgency: [normal|urgent|very_urgent], confidentiality: [public|confidential], entities: [{name, type}]}`
- **وابستگی:** T1.2, T1.5
- **نود دیاگرام:** Classifier

---

**T1.8 — VectorStore + Embedding**
- **مدت:** ۳ روز اجرا + ۱ روز Research
- **Research:** مقایسه nomic-embed-text vs multilingual-e5, benchmarking روی متن فارسی
- **تکنولوژی:** ChromaDB, nomic-embed-text via Ollama, LangChain text splitter
- **ورودی:** chunk‌های Document Parser
- **خروجی:** ChromaDB در حال اجرا + تابع `index_document(doc_id, chunks)` و `search(query, k=5)`
- **وابستگی:** T1.5, T1.2
- **نود دیاگرام:** VectorStore, Embedding Model

---

**T1.9 — RAG Pipeline**
- **مدت:** ۱ روز
- **Research پیش‌نیاز:** ندارد
- **تکنولوژی:** ChromaDB query + qwen3:8b + prompt template فارسی
- **ورودی:** query (string از کاربر)
- **خروجی:** `{answer: str, sources: [doc_id, ...]}`
- **وابستگی:** T1.8, T1.2
- **نود دیاگرام:** RAG Pipeline

---

### هفته ۴ (Days 22–30): MVP Integration

---

**T1.10 — Registration Agent**
- **مدت:** ۳ روز
- **Research پیش‌نیاز:** ندارد
- **تکنولوژی:** qwen3:8b FunctionCalling, tools: OCRTool + MetadataExtractorTool + DBInsertTool
- **ورودی:** فایل سند (PDF/DOCX/JPG)
- **خروجی:** `{registration_id: str, metadata: dict, status: "registered"}`
- **وابستگی:** T1.4, T1.6, T1.3
- **نود دیاگرام:** Registration Agent

---

**T1.11 — MVP UI (Streamlit)**
- **مدت:** ۳ روز
- **Research پیش‌نیاز:** ندارد
- **تکنولوژی:** Streamlit 1.32+, httpx (API calls)
- **ورودی:** FastAPI endpoints از T1.3 و T1.10
- **خروجی:** UI با قابلیت: آپلود سند → نمایش OCR → نمایش متادیتا → ثبت + جستجوی RAG
- **وابستگی:** T1.3, T1.10, T1.9
- **نود دیاگرام:** Web Upload UI

---

**T1.12 — MVP Integration Test + Demo Prep**
- **مدت:** ۲ روز
- **تکنولوژی:** pytest + httpx, demo script, docker-compose
- **ورودی:** همه components هفته‌های ۱-۴
- **خروجی:** سیستم MVP آماده نمایش با ۵ سند نمونه از پیش پردازش‌شده
- **وابستگی:** T1.11

---

## ماه دوم — Agentic Layer (Days 31–60)

> **هدف:** عامل‌های هوشمند، گردش‌کار خودکار، پیش‌نویس، Dashboard

---

### هفته ۵ (Days 31–37)

---

**T2.1 — Orchestrator (PlanAndExecuteAgent)**
- **مدت:** ۴ روز
- **Research:** ۱ روز (طراحی workflow graph نامه)
- **تکنولوژی:** qwen3:8b Function Calling, LangChain PlanAndExecute, custom tool registry
- **ورودی:** سند ورودی جدید
- **خروجی:** plan اجرایی → dispatch به Registration/Classification Agent
- **وابستگی:** T1.10, T1.7
- **نود دیاگرام:** Orchestrator

---

**T2.2 — Routing Agent**
- **مدت:** ۳ روز اجرا + ۱ روز Research
- **Research:** تهیه `org_chart.json` سازمان + تعریف قوانین ارجاع
- **تکنولوژی:** qwen3:8b ReAct, RoutingTool (code), org_chart.json, Human-in-the-loop approval endpoint
- **ورودی:** `{classification, org_chart}` → خروجی: `{destination, reason, confidence, requires_approval: true}`
- **وابستگی:** T2.1, T1.7
- **نود دیاگرام:** Routing Agent

---

### هفته ۶ (Days 38–44)

---

**T2.3 — Draft Generator + Drafting Agent**
- **مدت:** ۴ روز
- **Research:** ۰.۵ روز (جمع‌آوری قالب‌های نامه رسمی فارسی)
- **تکنولوژی:** qwen3:8b, RAGSkill (T1.9), قالب‌های Persian administrative, DraftingTool
- **ورودی:** نامه ورودی + نتایج RAG از مکاتبات قبلی
- **خروجی:** پیش‌نویس پاسخ رسمی فارسی (قابل ویرایش)
- **وابستگی:** T1.9, T2.1
- **نود دیاگرام:** Draft Generator, Drafting Agent

---

**T2.4 — LongTermMemory**
- **مدت:** ۲ روز
- **تکنولوژی:** Redis 7 (session), PostgreSQL (persistent), SQLAlchemy ORM, conversation schema
- **ورودی:** مکالمات و تصمیمات عامل‌ها
- **خروجی:** API: `save_memory(agent_id, data)` + `recall_memory(agent_id, query)`
- **وابستگی:** T1.1
- **نود دیاگرام:** LongTermMemory

---

**T2.5 — Deadline Agent + Notification**
- **مدت:** ۲ روز
- **تکنولوژی:** APScheduler, PostgreSQL (deadline table), SMTP, qwen3:8b (استخراج تاریخ از متن)
- **ورودی:** metadata از MetadataExtractor
- **خروجی:** scheduled jobs + email/in-app notification هشدار ۲ روز قبل از مهلت
- **وابستگی:** T1.6, T2.4
- **نود دیاگرام:** Deadline Agent, Notification Service

---

### هفته ۷ (Days 45–51)

---

**T2.6 — Document DB (MinIO + PostgreSQL)**
- **مدت:** ۲ روز
- **تکنولوژی:** MinIO (S3-compatible), PostgreSQL, SQLAlchemy, presigned URLs
- **ورودی:** فایل‌های پردازش‌شده + متادیتا
- **خروجی:** storage layer کامل + API: `store(file)` → `url`, `search_metadata(filters)` → `[docs]`
- **وابستگی:** T1.1
- **نود دیاگرام:** Document DB

---

**T2.7 — RBAC + Authentication**
- **مدت:** ۳ روز
- **تکنولوژی:** FastAPI + python-jose (JWT), PostgreSQL (roles table), Passlib (bcrypt)
- **ورودی:** user management requirements
- **خروجی:** roles: admin/manager/user + middleware احراز هویت روی همه endpoints
- **وابستگی:** T1.3

---

**T2.8 — Advanced RAG + Hybrid Search**
- **مدت:** ۲ روز
- **تکنولوژی:** ChromaDB metadata filtering, BM25 (keyword) + vector hybrid, reranking
- **ورودی:** ایندکس موجود
- **خروجی:** دقت جستجو بهبود یافته + فیلتر بر اساس date/sender/topic
- **وابستگی:** T1.9

---

### هفته ۸ (Days 52–60)

---

**T2.9 — Dashboard v1**
- **مدت:** ۴ روز
- **تکنولوژی:** React 18 + Recharts + Tailwind CSS + FastAPI endpoints
- **ورودی:** داده DB
- **خروجی:** Dashboard با: تعداد نامه‌ها، SLA status، نمودار موضوعات، لیست نامه‌های در انتظار
- **وابستگی:** T2.6
- **نود دیاگرام:** Dashboard

---

**T2.10 — Integration Testing**
- **مدت:** ۳ روز
- **تکنولوژی:** pytest + httpx + factory_boy (fixtures)
- **ورودی:** همه components ماه دوم
- **خروجی:** test suite با coverage > 70% + bug fixes

---

**T2.11 — Performance Baseline**
- **مدت:** ۲ روز
- **تکنولوژی:** Locust (load test), Prometheus + Grafana
- **خروجی:** metrics: latency p95 هر endpoint + throughput + GPU utilization

---

## ماه سوم — Production (Days 61–90)

> **هدف:** استقرار production-ready، fine-tuning، امنیت کامل، تحویل

---

### هفته ۹ (Days 61–67)

---

**T3.1 — Dashboard v2 + Analytics**
- **مدت:** ۴ روز
- **تکنولوژی:** React + Recharts + FastAPI (aggregation queries)
- **ورودی:** داده تاریخی ماه اول و دوم
- **خروجی:** analytics: KPI، trend نامه‌ها، پیش‌بینی ساده، export PDF گزارش
- **نود دیاگرام:** Dashboard

---

**T3.2 — Fine-tuning Research**
- **مدت:** ۳ روز Research
- **تکنولوژی:** unsloth, PEFT (LoRA), datasets کتابخانه HuggingFace
- **ورودی:** نامه‌های ثبت‌شده در سیستم (ماه ۱ و ۲)
- **خروجی:** dataset آماده‌شده + training script + محاسبه زمان/هزینه fine-tuning

---

### هفته ۱۰ (Days 68–74)

---

**T3.3 — qwen3:8b Fine-tuning**
- **مدت:** ۵ روز (۲ روز اجرا + ۳ روز آموزش + ارزیابی)
- **تکنولوژی:** unsloth + LoRA (r=16, alpha=32), qwen3:8b base, GPU 24GB+
- **ورودی:** dataset نامه‌های اداری فارسی سازمان + prompt template
- **خروجی:** مدل fine-tuned با بهبود در نگارش اداری فارسی + eval report
- **وابستگی:** T3.2

---

**T3.4 — Qdrant Migration (VectorStore)**
- **مدت:** ۲ روز
- **تکنولوژی:** Qdrant, migration script از ChromaDB
- **ورودی:** ChromaDB موجود
- **خروجی:** Qdrant در production با filtering پیشرفته‌تر
- **وابستگی:** T1.9

---

### هفته ۱۱ (Days 75–81)

---

**T3.5 — Production Deployment**
- **مدت:** ۴ روز
- **تکنولوژی:** Docker Compose (production), Nginx + SSL/TLS, Certbot, secrets management (`.env` + docker secrets)
- **ورودی:** همه سرویس‌ها
- **خروجی:** سیستم کامل روی سرور production قابل دسترسی از شبکه سازمان
- **نکته امنیتی:** Air-Gapped — هیچ درخواست خارجی مجاز نیست

---

**T3.6 — Load Testing + Optimization**
- **مدت:** ۳ روز
- **تکنولوژی:** Locust, cProfile, py-spy, GPU profiling
- **ورودی:** سیستم production
- **خروجی:** latency p95 < 3s برای OCR، < 1s برای جستجو + optimization patches

---

### هفته ۱۲ (Days 82–90)

---

**T3.7 — Documentation**
- **مدت:** ۳ روز
- **تکنولوژی:** MkDocs + Material theme, OpenAPI/Swagger auto-docs
- **خروجی:** مستندات فنی کامل + راهنمای استفاده + API reference

---

**T3.8 — Final QA + UAT**
- **مدت:** ۴ روز
- **تکنولوژی:** چک‌لیست دستی + کاربران واقعی سازمان
- **ورودی:** سیستم production-ready
- **خروجی:** bug list مرتب‌شده + sign-off کاربر

---

**T3.9 — Delivery + Handoff**
- **مدت:** ۲ روز
- **خروجی:** repository نهایی + مستندات + training session برای کاربران

---

## خلاصه تسک‌ها

| کد | عنوان | روز | ماه | نود دیاگرام |
|----|-------|-----|-----|-------------|
| T1.1 | Dev Environment | 3 | ۱ | FastAPI, DB |
| T1.2 | Ollama + Models | 3 | ۱ | model_dorna, model_qwen |
| T1.3 | FastAPI Scaffold | 2 | ۱ | FastAPI Gateway |
| T1.4 | V-OCR Integration | 4 | ۱ | V-OCR Module |
| T1.5 | Document Parser | 2 | ۱ | Document Parser |
| T1.6 | MetadataExtractor | 2.5 | ۱ | MetadataExtractor |
| T1.7 | Classifier | 3.5 | ۱ | Classifier |
| T1.8 | VectorStore + Embed | 4 | ۱ | VectorStore, Embed |
| T1.9 | RAG Pipeline | 1 | ۱ | RAG Pipeline |
| T1.10 | Registration Agent | 3 | ۱ | Registration Agent |
| T1.11 | MVP UI | 3 | ۱ | Web Upload UI |
| T1.12 | Demo Prep | 2 | ۱ | — |
| T2.1 | Orchestrator | 5 | ۲ | Orchestrator |
| T2.2 | Routing Agent | 4 | ۲ | Routing Agent |
| T2.3 | Draft + DraftAgent | 4.5 | ۲ | Drafter, DraftAgent |
| T2.4 | LongTermMemory | 2 | ۲ | LongTermMemory |
| T2.5 | Deadline + Notif | 2 | ۲ | DeadlineAgent, Notif |
| T2.6 | Document DB | 2 | ۲ | Document DB |
| T2.7 | RBAC + Auth | 3 | ۲ | FastAPI Gateway |
| T2.8 | Advanced RAG | 2 | ۲ | RAG Pipeline |
| T2.9 | Dashboard v1 | 4 | ۲ | Dashboard |
| T2.10 | Integration Test | 3 | ۲ | — |
| T2.11 | Performance | 2 | ۲ | — |
| T3.1 | Dashboard v2 | 4 | ۳ | Dashboard |
| T3.2 | Fine-tune Research | 3 | ۳ | model_qwen |
| T3.3 | Fine-tuning | 5 | ۳ | model_qwen |
| T3.4 | Qdrant Migration | 2 | ۳ | VectorStore |
| T3.5 | Production Deploy | 4 | ۳ | همه |
| T3.6 | Load Test | 3 | ۳ | — |
| T3.7 | Documentation | 3 | ۳ | — |
| T3.8 | Final QA | 4 | ۳ | — |
| T3.9 | Delivery | 2 | ۳ | — |

---

## برآورد هزینه ماهانه (لوکال GPU)

| مؤلفه | هزینه تقریبی/ماه |
|-------|-----------------|
| GPU Server (RTX 4090 cloud) | $200–400 |
| PostgreSQL + Redis (VPS) | $20–30 |
| MinIO Storage | $10–20 |
| **جمع** | **~$230–450/ماه** |

> اگر GPU local (owned) دارید: فقط هزینه برق + VPS ≈ $30–50/ماه
