## Legal Companion App

### End-to-End Architecture Flow (LegalTech AI)

```text
                ┌──────────────────────────┐
                │        Frontend UI       │
                │  (Lawyer Dashboard/Web)  │
                └────────────┬─────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │      API Gateway         │
                │ (Auth, Rate Limit, TLS)  │
                └────────────┬─────────────┘
                             │
         ┌───────────────────┼────────────────────┐
         ▼                   ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Contract Service│  │ Research Service│  │ Prediction Svc  │
│    (Python)     │  │    (Python)     │  │    (Python)     │
└───────┬─────────┘  └───────┬─────────┘  └───────┬─────────┘
        │                    │                    │
        ▼                    ▼                    ▼
 ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
 │ Document Svc │     │  RAG Service │     │ ML Model Svc │
 └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
        │                    │                    │
        ▼                    ▼                    ▼

 ┌──────────────────────────────────────────────────────────┐
 │                    DATA & AI LAYER                       │
 ├──────────────────────────────────────────────────────────┤
 │  S3 (Docs)   │ Vector DB │ PostgreSQL │   LLM Provider   │
 │ (Contracts)  │ (Embeds)  │ Metadata   │  (OpenAI/Llama)  │
 └──────────────────────────────────────────────────────────┘

                             ▲
                             │
                ┌────────────┴────────────┐
                │   Async Processing      │
                │   (Kafka / SQS Queue)   │
                └────────────┬────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │   Worker / Ingestion     │
                │ (OCR, Chunk, Embed)      │
                └──────────────────────────┘
```

### 1. Contract Analysis Flow

```text
User Upload → API Gateway → Contract Service
            → Document Service → S3

S3 Upload Event → Queue → Worker
               → Extract Text (OCR/Tika)
               → Chunk + Embed
               → Store in Vector DB

User Query → Contract Service → RAG Service
           → Retrieve Relevant Clauses
           → LLM Analysis
           → Response (Risks, Clauses, Suggestions)
```

### 2. Legal Research Flow

```text
User Query → API Gateway → Research Service
           → RAG Service
           → Embed Query
           → Search Vector DB (Cases + Laws)
           → Filter (Jurisdiction, Date)
           → LLM Summarization

Response:
- Case summaries
- Citations
- Legal insights
```

### 3. Case Prediction Flow

```text
User Input (Case Details)
        ↓
Prediction Service
        ↓
Feature Extraction
        ↓
ML Model Service (XGBoost / PyTorch)
        ↓
Prediction (Win/Loss/Settlement)
        ↓
LLM Explanation Layer
        ↓
Final Output (Prediction + Reasoning)
```

### 4. Continuous RAG Update Flow

To prevent response with outdated data:

```text
External Sources (Court APIs, Legal DBs)
        ↓
Scheduled Job (Cron / Airflow)
        ↓
Change Detection (Hashing)
        ↓
Queue (Kafka/SQS)
        ↓
Worker
   - Extract
   - Chunk
   - Embed
        ↓
Vector DB Update
        ↓
Metadata DB Update (PostgreSQL)
```


Production Design Patterns Used
Event-driven architecture → ingestion pipeline
Microservices → separation of concerns
RAG pattern → accurate legal answers
Hybrid AI (LLM + ML) → prediction + reasoning
CQRS-style separation → read (RAG) vs write (ingestion)