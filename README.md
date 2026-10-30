# Company Assistant

A chatbot for internal company questions. Employees ask in plain language, and the assistant decides whether the answer lives in **company records** (a Postgres database) or in **company documents** (the Clef employee handbook, this is some company's data that i have taken to work on this project), fetches it, and replies in natural language.

> Portfolio project, under active development.

## What it can answer

| Type | Example | Source |
|---|---|---|
| Record lookup | "What is the status of ticket 105?" | Postgres, through 38 read-only tools |
| Counts and lists | "How many employees do we have?" | Postgres |
| Policy question | "How many weeks of paid new parent leave are offered?" | Handbook, through RAG |
| Both at once | "What is the sabbatical policy, and what is the status of my leave request?" | Planned (see Roadmap) |
| Off topic or vague | "What's the weather?" | Canned reply or a clarification request |

## How it works
How it works

Every message goes through the same steps:

You type a message. It is added to the conversation history so follow-up questions work.
Intent classification. Mistral labels the message with one of five intents and rewrites it into a clean query for the right source. The prompt describes the 10 database tables and the handbook topics so the model can tell them apart.
Database_Query: the answer is stored in, or can be counted from, company records. Goes to the database path.
RAG_Query: the answer is a policy, benefit, rule or process. Goes to the handbook search path.
Mixed: needs both. Currently replies that it is not implemented yet.
Unclear: asks the user to rephrase.
Irrelevant: replies that it only helps with company topics.
Database path.
The model picks one tool out of 38 and extracts its arguments from the request.
Code checks the tool's required arguments. If any are missing, the bot lists them and asks you to resubmit. If no tool fits, it asks for clarification.
The tool runs a SQLAlchemy query against Postgres. If the query fails, the error text is kept instead of crashing the chat.
The result goes to the final answer step.
Handbook (RAG) path. The rewritten query is searched in Chroma and the top 8 handbook chunks are retrieved. The chunks go to the final answer step.
Final answer. Mistral receives your original question, the database result (together with the name of the tool and the arguments that produced it), and any retrieved chunks. It answers only from those, and says so plainly if the information is missing.
Reply. The answer is shown and added to the history, and the chat waits for the next message.

In short: message, then classify, then either database tools, handbook search, or a canned reply, then a final answer built from whatever was found.

The chatbot is read-only: it only has get_* and search_* tools.

## Tech stack

- **Orchestration:** LangGraph (state graph with conditional routing)
- **LLM:** Mistral `open-mistral-7b` through `langchain-mistralai`
- **Retrieval:** Chroma, `sentence-transformers` embeddings through `langchain-huggingface`, documents loaded with GitPython
- **Database:** PostgreSQL, SQLAlchemy 2, Alembic migrations, Faker for seed data (fake data for company)
- **API (in progress):** FastAPI, PyJWT, Argon2 password hashing
- **Tooling:** `uv`, Python 3.10+

## Getting started

```bash
git clone <your-repo-url>
cd Company_Project
uv sync
```

Create a `.env` file in the project root:

```env
MISTRAL_API_KEY=your_key_here
DATABASE_URL=<your postgres connection string>   # match the variable name your config reads
```

Set up the database, then start the chat:

```bash
# <migration and seed commands for your project, for example:>
# uv run alembic upgrade head
uv run python -m company_project.AI_Chat.chat
```

Type a question at the `You:` prompt, and `exit` to quit. Debug output shows every graph node, the chosen tool and its arguments. Set `DEBUG=False` in `chat.py` to silence it.

The first run builds the handbook vector store. <describe how you trigger ingestion if it is a separate step>

## Evaluation

The RAG pipeline has its own test harness, `src/company_project/AI_Chat/test_rag_eval.py`, with a 50-question dataset built from the handbook: 10 direct, 10 paraphrased, 10 specific-detail, 10 multi-part, and 10 unanswerable questions. Every reference answer carries the exact evidence passage and source file.

```bash
uv run python -m company_project.AI_Chat.test_rag_eval --chat-module company_project.AI_Chat.chat --mode retrieval
uv run python -m company_project.AI_Chat.test_rag_eval --chat-module company_project.AI_Chat.chat --mode intent
uv run python -m company_project.AI_Chat.test_rag_eval --chat-module company_project.AI_Chat.chat --mode e2e --judge
```

| Mode | What it measures |
|---|---|
| `retrieval` | Raw question to vector store: file hit@k, evidence hit@k, MRR, full evidence coverage |
| `intent` | Intent routing only, with built-in control questions so a fix cannot just send everything to RAG |
| `e2e` | The whole graph: routing, rewritten query, retrieved chunks, answer quality, and whether unanswerable questions are declined instead of invented |

Retrieval results on the 40 answerable questions (8 chunks retrieved):

| Metric | Result |
|---|---|
| Right document in top 5 | 0.97 |
| Answer passage in top 3 / top 8 | 0.85 / 0.93 |
| Answer passage ranked first | 0.60 |
| MRR | 0.72 |

Unanswerable questions were declined correctly in 10 of 10 end-to-end cases. Answer correctness is graded by the same 7B model, so treat it as a soft signal.

What improved retrieval: removing files that only contained links to other documents, no longer indexing headings as separate chunks, and iterating on queries against the evaluation set.

## Project layout

```
src/company_project/
├── AI_Chat/
│   ├── chat.py            # LangGraph app: intent, routing, tools, answer
│   ├── tools/             # LangChain tools, one module per table
│   ├── Vector_db/         # Chroma store and handbook ingestion
│   └── test_rag_eval.py   # Evaluation harness
└── queries/               # SQLAlchemy query functions behind the tools
```

## Roadmap

- [ ] Run **Mixed** queries by executing the database and RAG branches in parallel and merging the answer
- [ ] Use the logged-in user (from the JWT) for "my" questions, and enforce permissions in code before any tool runs
- [ ] Serve the chatbot through FastAPI and build a web UI
- [ ] Admin dashboard for creating, updating and deleting records (the chatbot itself stays read-only)
- [ ] Retrieval ranking: reranker and chunk-size experiments
- [ ] Try a stronger model for intent classification and tool selection

## Acknowledgements

The handbook corpus is the public [Clef employee handbook](https://github.com/clef/handbook). All company data in the database is fake, generated with Faker.