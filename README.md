# Company Assistant

A chatbot for internal company questions. Employees ask in plain language, and the assistant decides whether the answer lives in **company records** (a Postgres database) or **company documents** (the Clef employee handbook, public data used to build this project), fetches it, and replies in natural language. It knows who is asking, enforces role-based permissions, and degrades gracefully when the LLM or database fails.

> Portfolio project, under active development.

## What it can answer

| Type | Example | Source |
|---|---|---|
| Record lookup | "What is the status of ticket 105?" | Postgres, through 39 read-only tools |
| "My" questions | "How many annual leave days do I have left?" | Postgres, scoped to the logged-in user |
| Counts and lists | "How many employees do we have?" | Postgres |
| Policy question | "How many weeks of paid new parent leave are offered?" | Handbook (RAG) |
| Both at once | "What is the sabbatical policy, and what is the status of my leave request?" | Both, answered together |
| Off topic or vague | "What's the weather?" | Canned reply or a clarification request |

The chatbot is read-only: it only has `get_*` and `search_*` tools.

## How it works

1. **Intent classification.** The LLM labels the message (`Database_Query`, `RAG_Query`, `Mixed`, `Unclear`, `Irrelevant`) and rewrites it into a standalone query for each source.
2. **Handbook path.** Semantic cache lookup, then on a miss Chroma returns the top 8 chunks, then the answer is generated and cached.
3. **Database path.**
   - The LLM picks one of 39 tools and extracts its arguments.
   - "My" questions are filled in from the logged-in user, never from the model.
   - A role-based permission check runs before any tool executes.
   - Missing arguments are requested from the user, then the tool runs.
4. **Mixed** questions run both paths in parallel and are merged into one answer.
5. **Final answer.** The LLM answers only from the retrieved records and chunks, and says so plainly when information is missing.

## Features

- **Auth and permissions:** JWT login with Argon2 password hashes. The user is loaded from the database on every request, and inactive accounts are rejected. Role checks (`auth/authorization.py`) run before every tool call.
- **Admin-only CRUD API:** the REST endpoints (employees, assets, tickets, and so on) require the admin role, checked against the database on every request. `/chat` is open to any logged-in employee and is protected per tool.
- **Better retrieval:**
  - Link-only files and standalone headings are no longer indexed.
  - Every chunk is prefixed with `Document / Section` context (RAGAS context recall rose from 0.80 to 0.95).
  - Ingestion is incremental, using file hashes plus a manifest. A config change triggers a full rebuild.
- **Semantic cache (RAG only):**
  - Database and user-specific answers are never cached.
  - Matching uses embeddings of the rewritten query (`bge-base-en-v1.5`), stored in a separate Chroma collection with a cosine threshold of 0.92.
  - The threshold was tuned on 124 labelled question pairs (`tune_cache_threshold.py`): no false hits at 0.90 or above, with 39% of paraphrases served from cache at 0.92.
  - Entries are versioned by a hash of the ingestion manifest, models and prompt version, so re-ingesting the handbook invalidates old answers. They also expire after 7 days.
- **Concurrency-safe API:**
  - One message at a time per conversation (per-conversation lock).
  - A global cap on simultaneous graph runs, which protects LLM rate limits and the DB pool (the pool is sized for concurrent requests).
  - A bounded in-memory conversation store.
  - Input size limits.
  - Busy requests get a 409 or 503.
- **Error handling (`resilience.py`):**
  - LLM and database calls are retried with exponential backoff and jitter.
  - Errors are classified (rate limit, timeout, connection, server, auth, bad output, database).
  - Users get safe messages, never stack traces.
  - If document search fails, the bot says so instead of guessing.
  - In `Mixed` questions, the part that worked is still answered.
- **Tool descriptions:** each tool says when to use it and when not to (for example, get-by-ID vs. search), and tools return the arguments they ran with so the answer can be verified.

## Tech stack

- **Orchestration:** LangGraph, LangChain
- **LLM:** Gemini 2.5 Flash (`langchain-google-genai`); Mistral `open-mistral-7b` (`langchain-mistralai`) as the RAGAS judge
- **Retrieval:** Chroma (`langchain-chroma`); `bge-small-en-v1.5` embeddings for the handbook index and `bge-base-en-v1.5` for the cache, through `sentence-transformers` and `langchain-huggingface`; handbook loaded with GitPython and `langchain-community`
- **Database:** PostgreSQL (`psycopg` 3), SQLAlchemy 2, Alembic migrations, Faker for seed data
- **API and auth:** FastAPI, Uvicorn, Pydantic, PyJWT, Argon2 (`pwdlib`)
- **Evaluation and tests:** RAGAS, pandas, pytest
- **Tooling:** `uv`, `python-dotenv`, Python 3.10+

## Getting started

```bash
git clone https://github.com/yashfeens3018-personal/Company_Chatbot
cd Company_Chatbot
uv sync
```

Create a `.env` in the project root:

```env
GOOGLE_API_KEY=your_key_here
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/dbname
JWT_SECRET_KEY=a_long_random_string
MISTRAL_API_KEY=your_key_here   # optional: only the RAGAS evaluation judge uses it
```

Set up and run (from the project root, since paths like `./chroma_langchain_db` are relative):

```bash
uv run alembic upgrade head                                     # create tables
uv run python -m company_project.database.seed                  # fake company data
uv run python -m company_project.AI_Chat.Vector_db.ingestion    # build the handbook index
uv run uvicorn company_project.main:app                         # API, run a SINGLE worker
```

- **API:** `POST /token/login` returns a token. Send it as `Authorization: Bearer <token>` to `POST /chat` with `{"message": "...", "conversation_id": null}`. Reuse the returned `conversation_id` for follow-ups. The CRUD endpoints (`/employees`, `/tickets`, ...) need a token from an account with the admin role.
- **Terminal chat (alternative):** `uv run python -m company_project.AI_Chat.chat`, then log in with an employee email. Debug output (every graph node, tool and argument) is off by default; set `CHAT_DEBUG=1` to turn it on.
- **After changing the handbook:** stop the server, re-run ingestion, start the server again. The running app keeps the index it loaded at startup, and a restart also invalidates the cache.

## Evaluation

Harness: `src/company_project/AI_Chat/rag_eval/`, with a 50-question dataset built from the handbook (10 each: direct, paraphrased, specific-detail, multi-part, unanswerable). Every reference answer carries its evidence passage and source file.

```bash
uv run python -m company_project.AI_Chat.rag_eval.test_rag_eval --chat-module company_project.AI_Chat.chat --mode retrieval
uv run python -m company_project.AI_Chat.rag_eval.test_rag_eval --chat-module company_project.AI_Chat.chat --mode intent
uv run python -m company_project.AI_Chat.rag_eval.test_rag_eval --chat-module company_project.AI_Chat.chat --mode e2e --judge
```

| Mode | What it measures |
|---|---|
| `retrieval` | Question to vector store: file hit@k, evidence hit@k, MRR, full evidence coverage |
| `intent` | Routing only, with control questions so a fix can't just send everything to RAG |
| `e2e` | The whole graph: routing, retrieved chunks, answer quality, and declining unanswerable questions |

Baseline retrieval on the 40 answerable questions (8 chunks, before section context was added to chunks):

| Metric | Result |
|---|---|
| Right document in top 5 | 0.97 |
| Answer passage in top 3 / top 8 | 0.85 / 0.93 |
| Answer passage ranked first | 0.60 |
| MRR | 0.72 |

RAGAS on the 38 scored answerable questions (judge: `open-mistral-7b`, so treat scores as soft signals):

| Metric | Run 1: baseline | Run 2: chunk context added |
|---|---|---|
| Faithfulness | 0.84 | 0.93 |
| Answer relevancy | 0.77 | 0.82 |
| Context precision | 0.61 | 0.68 |
| Context recall | 0.80 | 0.95 |

Prefixing each chunk with its document title and section was the biggest single win. A reranker (top 10 to 5, and top 20 to 7) was tested and dropped: precision did not improve, multi-part precision actually fell, and it added latency. Multi-part precision (0.36) is the main known weakness. Recall is high, so the right passages are retrieved but ranked among extra chunks.

All runs are saved in `RAG_EVALUATION/` (start with `RAG_EVALUATION_RUNS_SUMMARY.txt`). Unanswerable questions were declined correctly in 10 of 10 end-to-end cases.

Concurrency tests (fake graph, no LLM calls): `uv run pytest tests/test_chat_concurrency.py -v`. They cover lost messages, cross-user isolation, bounded memory, the run cap, and failure recovery.

More detail on problems hit and how they were fixed: `ProblemsFaced_and_solved.txt`.

## Project layout

```
src/company_project/
├── main.py            # FastAPI app and login
├── api/               # REST routers and the /chat endpoint
├── auth/              # JWT, password hashing, role-based authorization
├── database/          # models, engine, seed data
├── queries/           # SQLAlchemy query functions behind the tools
└── AI_Chat/
    ├── chat.py        # LangGraph app: intent, routing, tools, answer
    ├── cache.py       # semantic cache for handbook answers
    ├── resilience.py  # retries and error handling
    ├── tools/         # LangChain tools, one module per table
    ├── Vector_db/     # Chroma store and incremental ingestion
    └── rag_eval/      # evaluation harness, datasets, cache threshold tuning
RAG_EVALUATION/        # saved evaluation runs
tests/                 # concurrency tests
alembic/               # migrations
```

Created at runtime : `data/` (handbook clone), `chroma_langchain_db/` (handbook index), `rag_cache_db/` (semantic cache).

## Known limits and roadmap

- [x] Logged-in user for "my" questions, with permissions enforced before any tool runs
- [x] Mixed (database + handbook) questions
- [x] Lock the CRUD REST endpoints to the admin role
- [ ] Store conversations in the database (they currently live in server memory and reset on restart, so run one worker)
- [ ] Tools that chain (look up an ID by name, then use it)
- [ ] Sub-query splitting or MMR for multi-part handbook questions (a reranker was tried and dropped)
- [ ] Constrain the query rewriter, which rewrites most questions and sometimes adds or drops details
- [ ] Web UI and an admin dashboard

## Acknowledgements

The handbook corpus is the public [Clef employee handbook](https://github.com/clef/handbook). All company data in the database is fake, generated with Faker.
