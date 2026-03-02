# Pravaha — Agentic Slack AI

> An autonomous, tool-using AI assistant embedded in Slack, powered by Claude claude-sonnet-4-6 with Retrieval-Augmented Generation (RAG), multi-turn memory, and a suite of real-time tools.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.x-green)](https://djangoproject.com)
[![Deployed on Railway](https://img.shields.io/badge/Deployed%20on-Railway-blueviolet)](https://railway.app)

---

## Overview

Pravaha is a production-grade agentic AI system integrated into Slack. Unlike simple chatbots that pipe a prompt through an LLM and return a fixed response, Pravaha runs an **agentic tool-use loop**: it reasons about what information it needs, selects and invokes tools, observes results, and iterates — all before composing a final answer. It maintains per-thread conversational memory and can answer questions grounded in your internal document library via RAG.

---

## Architecture

```
Slack Event / Slash Command
         │
         ▼
  Django (Gunicorn)          ← receives webhook, validates Slack signature
         │
         ▼
  Celery Task (Redis)        ← async processing, adds 🧠 reaction while thinking
         │
         ▼
  Agent Loop (Claude claude-sonnet-4-6)
  ┌───────────────────────────────────────┐
  │  1. Build message + conversation history│
  │  2. Call Anthropic API with tool defs  │
  │  3. If tool_use → invoke tool          │
  │  4. Feed result back → repeat          │
  │  5. Return final text response         │
  └───────────────────────────────────────┘
         │
         ▼
  Slack Block Kit Response   ← rich formatted reply with tool-use footer
```

### Components

| Layer | Technology | Why |
|---|---|---|
| **Web server** | Django + Gunicorn | Battle-tested, easy Celery integration, robust middleware |
| **Async tasks** | Celery + Redis | Slack requires HTTP 200 in < 3s; tasks run in a separate worker process |
| **AI brain** | Anthropic Claude claude-sonnet-4-6 | Best-in-class reasoning, native tool-use API, long context |
| **RAG embeddings** | `sentence-transformers` (BAAI/bge-small-en-v1.5) | Free, runs on CPU, 384-dim, no external API key needed |
| **Vector store** | Upstash Vector | Serverless, HTTP-native, free tier sufficient for most teams |
| **Conversation memory** | Django ORM (SQLite → Postgres-ready) | Persistent, queryable, no extra infrastructure |
| **Deployment** | Railway | Git-push deploys, managed Redis, env var injection, zero DevOps overhead |

---

## Features

### Agentic Tool-Use Loop
The core of Pravaha is an autonomous reasoning loop (`agent.py`). On each turn:
1. Claude receives the user message and full conversation history
2. Claude decides whether to answer directly or call one or more tools
3. Tool results are fed back into context
4. The loop runs up to 10 iterations, with a graceful fallback if the limit is hit

This means the bot can **chain multiple tools** — e.g., search the web for context, then run Python to crunch numbers, then query the knowledge base to cross-reference internal docs — all in a single response.

### Available Tools

| Tool | Description |
|---|---|
| `search_web` | DuckDuckGo web search — no API key, real-time results |
| `execute_python` | Sandboxed Python subprocess execution, 15s timeout |
| `query_knowledge_base` | Semantic search over indexed internal documents via RAG |
| `get_current_datetime` | Current date/time in any timezone (pytz) |
| `get_weather` | Live weather via wttr.in — no API key |
| `get_slack_channel_history` | Reads recent messages from any Slack channel |
| `fetch_url_content` | Fetches and parses any webpage (BeautifulSoup) |

### Retrieval-Augmented Generation (RAG)
Pravaha answers questions from your internal documents without hallucinating. The pipeline:

1. **Indexing** (`manage.py index_documents --path /your/docs`):
   - Loads PDF, TXT, MD, DOCX files with LlamaIndex `SimpleDirectoryReader`
   - Embeds each chunk using `BAAI/bge-small-en-v1.5` (384-dim, runs locally)
   - Upserts vectors + metadata directly to Upstash via the `upstash-vector` client

2. **Querying** (at inference time):
   - Embeds the user's question with the same model
   - Queries Upstash for top-5 nearest neighbours
   - Returns raw text chunks with similarity scores to Claude
   - Claude synthesises the final answer — no LLM used in the retrieval step itself

**Why this approach?** Separating the retrieval (semantic search) from generation (Claude) gives full control over both steps and avoids the overhead of a local LLM synthesizer.

### Multi-Turn Conversation Memory
Every message is stored in the `ConversationMessage` model, keyed by:
- **DMs**: `channel_id` (persistent across all DMs with the bot)
- **Channel threads**: `thread_ts` (scoped to a specific thread)
- **Top-level mentions**: `message_ts`

This means the bot remembers context across an entire thread without re-indexing.

### Slack Block Kit Responses
All responses use Slack's Block Kit for rich formatting:
- Long responses are split across multiple `section` blocks (Slack's 3000-char limit)
- A footer block shows which tools were used (e.g., `🔍 search_web · 🐍 execute_python`)
- A 🧠 reaction is added while the bot thinks, removed when done

---

## Project Structure

```
Slack_ai_pravaha/
├── Procfile                          # Railway: web + worker process definitions
├── requirements.txt                  # Python dependencies
├── runtime.txt                       # python-3.12
└── src/
    ├── manage.py
    ├── akhome/
    │   ├── settings.py               # Django settings (env-var driven)
    │   ├── urls.py                   # URL routing
    │   └── celery.py                 # Celery app config
    ├── pravahabot/
    │   ├── agent.py                  # Core agentic Claude loop
    │   ├── ai.py                     # RAG query (embeddings + Upstash)
    │   ├── blocks.py                 # Slack Block Kit builders
    │   ├── models.py                 # ConversationMessage ORM model
    │   ├── tasks.py                  # Celery tasks: process_slack_message, process_slash_command
    │   ├── views.py                  # Django views: events endpoint, slash command endpoint
    │   ├── tools/
    │   │   ├── search.py             # DuckDuckGo web search
    │   │   ├── code.py               # Python code execution
    │   │   ├── knowledge.py          # RAG knowledge base wrapper
    │   │   ├── slack.py              # Slack channel history reader
    │   │   └── misc.py               # datetime, weather, URL fetcher
    │   └── management/commands/
    │       └── index_documents.py    # One-time document indexing CLI
    ├── slacky/
    │   └── messages.py               # Slack API client (send, react, slash response)
    └── helpers/
        └── env.py                    # AutoConfig env var loader (file + os.environ)
```

---

## Local Development

### Prerequisites
- Python 3.12
- Redis (for Celery)
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

```bash
# Clone and enter project
git clone https://github.com/AkshatSharma03/Slack_ai_pravaha.git
cd Slack_ai_pravaha

# Create venv and install deps
uv venv src/.venv --python 3.12
uv pip install -r requirements.txt --python src/.venv/bin/python

# Create env file
cp src/.env.example src/.env   # then fill in your values

# Run migrations
src/.venv/bin/python src/manage.py migrate

# Index your documents (optional)
src/.venv/bin/python src/manage.py index_documents --path /path/to/your/docs
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Claude API key from console.anthropic.com |
| `SLACK_BOT_OAUTH_TOKEN` | ✅ | Bot token from api.slack.com (xoxb-…) |
| `SLACK_SIGNING_SECRET` | ✅ | Signing secret from Slack app Basic Information |
| `UPSTASH_VECTOR_REST_URL` | ✅ | Upstash vector index REST URL |
| `UPSTASH_VECTOR_REST_TOKEN` | ✅ | Upstash vector index REST token |
| `CELERY_BROKER_URL` | ✅ | Redis URL (e.g. `redis://localhost:6379/0`) |
| `DJANGO_SECRET_KEY` | ✅ | Django secret key (generate with `secrets.token_urlsafe(50)`) |
| `DJANGO_DEBUG` | ❌ | `True` for dev, `False` for production |
| `ALLOWED_HOSTS` | ❌ | Comma-separated allowed hostnames |

### Running Locally

```bash
# Terminal 1 — Django web server
src/.venv/bin/python src/manage.py runserver

# Terminal 2 — Celery worker
src/.venv/bin/celery -A akhome worker -l info --concurrency 2

# Expose to Slack via ngrok (for local testing)
ngrok http 8000
# Then update your Slack app's Event Subscriptions URL to the ngrok URL
```

---

## Deployment (Railway)

The app ships with a `Procfile` that defines two processes:

```
web:    cd src && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn akhome.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
worker: cd src && celery -A akhome worker -l info --concurrency 2
```

### Steps
1. Push to GitHub
2. Create a Railway project, add a **Redis** service
3. Add a service from your GitHub repo (the `web` process)
4. Add a second service from the same repo, override start command to the `worker` line
5. Set all environment variables in both services (reference Redis's `REDIS_URL` for `CELERY_BROKER_URL`)
6. Run `railway up` or push to trigger a deploy

### Slack App Configuration
After deploying, update your Slack app at [api.slack.com/apps](https://api.slack.com/apps):

- **Event Subscriptions** → Request URL: `https://<your-domain>/pravahabot/events/`
  - Subscribe to: `app_mention`, `message.im`
- **Slash Commands** → Create `/pravaha` pointing to `https://<your-domain>/pravahabot/slash/`
- **OAuth Scopes** needed: `app_mentions:read`, `channels:history`, `chat:write`, `commands`, `im:history`, `im:read`, `im:write`, `reactions:write`, `users:read`

---

## Tech Stack Decisions

**Claude claude-sonnet-4-6 over GPT-4**: Native tool-use via the Anthropic API is cleaner and more reliable for agentic loops. The `tool_use` / `tool_result` content blocks make multi-step reasoning straightforward to implement without external orchestration frameworks.

**Celery + Redis over async Django**: Slack's 3-second response window makes synchronous LLM calls impossible. Celery lets the view return immediately, while a worker processes the full agentic loop in the background. Redis provides both the message broker and result backend in a single service.

**Upstash Vector over Pinecone/Weaviate**: Upstash is serverless and HTTP-native — no persistent connection management, no SDK version hell, and a generous free tier. The direct REST API also makes it trivial to upsert and query without an ORM abstraction.

**BAAI/bge-small-en-v1.5 over OpenAI Ada**: Eliminates a paid API dependency for embeddings. At 384 dimensions it's fast on CPU, the quality is competitive for retrieval tasks, and it runs entirely within the Railway container with no external calls at inference time.

**Direct `upstash-vector` client over LlamaIndex storage**: LlamaIndex's `VectorStoreIndex.from_documents()` adds abstraction that can silently fail (confirmed: 0 vectors written despite a success message). Talking directly to Upstash via `Index.upsert()` and `Index.query()` is explicit, debuggable, and has no hidden failure modes.

**Django ORM for conversation memory**: A simple relational model (`ConversationMessage` keyed by `thread_ts` + `channel_id`) is enough for per-thread memory. Avoids running a separate key-value store, and the data is queryable/exportable if needed.

---

## License

MIT
