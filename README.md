# Code Assistant: Hybrid RAG

Code Assistant is a Retrieval-Augmented Generation (RAG) application for asking questions about an indexed codebase or document collection. It combines dense vector search, sparse keyword search, cross-encoder reranking, and an LLM-generated answer with optional source snippets.

The project includes:

- A FastAPI backend for authentication, ingestion, health checks, and question answering.
- A static HTML/CSS/JavaScript frontend in `app/frontend`.
- Chroma Cloud for vector storage.
- Google Gemini embeddings.
- BM25 keyword retrieval and a cross-encoder reranker.
- Groq-hosted LLM generation.
- Supabase authentication and an Aiven PostgreSQL database for user and query records.
- Optional LangSmith tracing.

## Engineering Highlights

- **Hybrid retrieval:** combines semantic vector search with BM25 keyword retrieval to cover both conceptual and exact-code queries.
- **Retrieval fusion + reranking:** candidate results are combined and then refined with a cross-encoder before generation.
- **Source-grounded generation:** the LLM receives the most relevant retrieved context and can return source snippets with the answer.
- **Production API:** FastAPI provides authentication, ingestion, health checks and synchronous/streaming Q&A endpoints.
- **User isolation:** Supabase authentication protects user-facing operations and PostgreSQL stores application/query data.
- **Observability:** optional LangSmith tracing makes the RAG pipeline easier to inspect and debug.
- **Deployable architecture:** the backend, frontend and external vector/database services are separated so the system can be deployed independently.

## How It Works

```text
Document upload
      |
      v
Load and chunk documents
      |
      v
Gemini embeddings ---> Chroma Cloud
      |                      |
      +---- BM25 -----------+
                 |
                 v
        Hybrid ensemble retrieval
                 |
                 v
          Cross-encoder reranking
                 |
                 v
          Groq LLM answer generation
```

For a question, the retriever combines semantic vector results and keyword results, reranks the candidates, and sends the relevant context to the LLM. The API can return the answer with the retrieved source snippets.

## Project Structure

```text
Hybrid_rag/
├── app/
│   ├── backend/
│   │   ├── router.py             # FastAPI application and API routes
│   │   └── auth/
│   │       ├── oauth.py          # Signup, login, and current-user routes
│   │       └── security.py       # Supabase bearer-token validation
│   └── frontend/
│       ├── index.html            # Static chat interface
│       ├── styles.css            # Frontend styling
│       └── app.js                # API, auth, upload, and chat client
├── hybrid_rag_pipeline/
│   ├── Database/
│   │   ├── chroma_db.py          # Chroma Cloud client and chunk storage
│   │   ├── models.py             # SQLAlchemy models
│   │   └── relational_db.py      # PostgreSQL engine and sessions
│   ├── ingest/
│   │   └── processing.py         # Document loading and chunking
│   └── rag/
│       ├── generation/main.py    # LLM and RAG chain setup
│       └── retriever/
│           ├── retrieval.py      # Vector + BM25 retrieval
│           └── rerank.py         # Cross-encoder reranking
├── requirements.txt
├── .env.example
└── readme.md
```

## Requirements

- Python 3.14 or a compatible recent Python version.
- A Chroma Cloud account.
- A Google AI Studio API key.
- A Groq API key.
- A Supabase project for authentication.
- A PostgreSQL database, such as Aiven PostgreSQL.
- Optional: a LangSmith account for tracing.

## Installation

From the project root:

```bash
git clone https://github.com/krk-90/CODEBASE-ASSISTANT-powered-by-HYBRID_RAG.git
cd CODEBASE-ASSISTANT-powered-by-HYBRID_RAG

python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

The database and authentication modules also require these packages if they are not already installed:

```bash
pip install sqlalchemy asyncpg supabase
```

On Windows, if PowerShell blocks activation, run this in the current terminal before activating:

```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## Environment Configuration

Create `.env` in the project root. Start from `.env.example`, then replace each placeholder with a real value.

```env
GOOGLE_API_KEY=your_google_api_key
GROQ_API_KEY=your_groq_api_key

CHROMA_API_KEY=your_chroma_api_key
CHROMA_TENANT=your_chroma_tenant
CHROMA_DATABASE=your_chroma_database
CHROMA_COLLECTION=document_embed

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key

DATABASE_URL=postgresql+asyncpg://username:password@host:port/database?sslmode=require

LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=rag-tracing
LANGCHAIN_API_KEY=your_langsmith_api_key

CORS_ALLOWED_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
```

For an Aiven PostgreSQL URL, the application accepts the regular Aiven `sslmode=require` form and converts it for `asyncpg` internally. The URL must use the `postgresql+asyncpg` SQLAlchemy driver:

```env
DATABASE_URL=postgresql+asyncpg://avnadmin:YOUR_PASSWORD@YOUR_AIVEN_HOST:YOUR_PORT/defaultdb?sslmode=require
```

Never commit `.env` or expose database passwords and API keys. Rotate credentials that have been shared publicly.

## Start Locally

### 1. Start the backend

Use port `8000`, which is the frontend default:

```bash
# Activate the virtual environment first, then:
uvicorn app.backend.router:app --reload --host 127.0.0.1 --port 8000
```

The backend performs database initialization and loads the LLM, Chroma client, retriever, and RAG chain during startup. A failed database connection or missing provider credential will prevent startup.

### 2. Start the frontend

The frontend is static and does not use `npm start` or require a `package.json`.

From a second terminal:

```bash
cd app/frontend
python -m http.server 5500
```

Open:

```text
http://127.0.0.1:5500/
```

VS Code Live Server can also serve `app/frontend/index.html`. If the backend runs on another port, update `API_BASE` at the top of `app/frontend/app.js`:

```javascript
const API_BASE = 'http://localhost:8001';
```

### 3. Verify the backend

Open these URLs:

- `http://127.0.0.1:8000/` - service welcome response.
- `http://127.0.0.1:8000/health` - LLM, retriever, and RAG readiness.
- `http://127.0.0.1:8000/docs` - interactive Swagger API documentation.

The health response should contain `true` for all three readiness fields before asking questions.

## Frontend Features

The Code Assistant frontend supports:

- Email/password signup and login through Supabase.
- Persistent access-token storage in browser local storage.
- Logout and current-user restoration.
- Pipeline health status.
- Uploading PDF, DOCX, PNG, JPG, and TXT files.
- Asking authenticated questions.
- Optional retrieved-source display.
- Responsive desktop and mobile layouts.

The frontend sends API requests to `http://localhost:8000` by default. The backend CORS configuration must include the frontend origin.

## API Reference

### `GET /`

Returns a simple service message.

### `GET /health`

Returns readiness information:

```json
{
  "llm_ready": true,
  "retriever_ready": true,
  "rag_chain_ready": true
}
```

### `POST /auth/signup`

Creates a Supabase account.

```json
{
  "email": "user@example.com",
  "password": "strong-password"
}
```

Depending on Supabase email-confirmation settings, the response may contain an access token immediately or require email confirmation first.

### `POST /auth/login`

Signs in a user and returns a bearer token.

```json
{
  "email": "user@example.com",
  "password": "strong-password"
}
```

Use the returned token on protected requests:

```text
Authorization: Bearer <access_token>
```

### `GET /auth/me`

Returns the authenticated Supabase user. Requires a bearer token.

### `POST /ingest`

Uploads and indexes one supported file. Supported extensions are `.pdf`, `.docx`, `.png`, `.jpg`, and `.txt`.

```bash
curl -X POST "http://127.0.0.1:8000/ingest" -F "file=@docs/manual.pdf"
```

The response includes the filename and number of stored chunks. Ingestion refreshes the BM25 index and RAG chain afterward.

### `POST /query`

Asks an authenticated question.

```json
{
  "query": "How does authentication work?",
  "k": 4,
  "show_sources": true
}
```

Example response:

```json
{
  "answer": "...",
  "sources": [
    {
      "source": "auth/security.py",
      "page": null,
      "snippet": "..."
    }
  ]
}
```

### `POST /query/stream`

Streams answer chunks as Server-Sent Events. It requires the same bearer token and request body as `/query`.

## Command-Line Usage

### Ingest documents

```bash
python -m hybrid_rag_pipeline.ingest.processing --path ./docs/manual.pdf
python -m hybrid_rag_pipeline.ingest.processing --path ./docs --chunk_size 1000 --over_lap 200
```

### Inspect or query retrieval

```bash
python -m hybrid_rag_pipeline.rag.retriever.retrieval --inspect --limit 20
python -m hybrid_rag_pipeline.rag.retriever.retrieval --query "authentication flow" --k 6 --json
```

Useful retrieval options include `--no-rerank`, `--refresh-bm25`, `--fetch-k`, `--limit`, and `--json`.

### Ask through the RAG chain

```bash
python -m hybrid_rag_pipeline.rag.generation.main "Explain the reranking step"
python -m hybrid_rag_pipeline.rag.generation.main "How does auth work?" --show-sources
```

## Troubleshooting

### `npm start` reports that `package.json` is missing

This is a static frontend, not a React or Node application. Use Python HTTP Server or VS Code Live Server instead.

### The page shows `Pipeline unavailable`

Check that the backend is running, the frontend calls the same port, and `/health` is reachable. Confirm that `CORS_ALLOWED_ORIGINS` includes `http://127.0.0.1:5500`.

### PostgreSQL connection timeout

Confirm the Aiven service is running, copy the current connection details, and test the configured host and port:

```bash
Test-NetConnection YOUR_DATABASE_HOST -Port YOUR_DATABASE_PORT
```

If `TcpTestSucceeded` is `False`, check Aiven network access, public connectivity, firewall rules, and the database endpoint.

### `asyncpg` rejects `sslmode`

Use `postgresql+asyncpg` in `DATABASE_URL`. The project converts `sslmode=require` to the `asyncpg`-compatible `ssl=require` form before creating the engine.

### The API fails while importing Supabase

Check `SUPABASE_URL` and `SUPABASE_ANON_KEY`, and install the `supabase` package in the active virtual environment.

### The API fails during startup while loading the RAG chain

Check Chroma, Google, and Groq credentials. The backend initializes external services during application startup, so missing provider credentials can stop the server before it accepts requests.

## Rate Limits and Operational Notes

- Ingestion is limited to 5 requests per minute.
- Query endpoints are limited to 10 requests per minute.
- The BM25 index is held in process memory and is refreshed after ingestion.
- Startup loads the model and retriever once and reuses them across requests.
- Large ingestion jobs should eventually use a background job queue.
- The current streaming endpoint uses Server-Sent Events; a WebSocket alternative is not implemented.
- Do not expose the development server directly to the public internet without production authentication, HTTPS, secret management, and a production process manager.

## Deployment Checklist

1. Store secrets in the deployment provider's environment settings, not in the repository.
2. Set `DATABASE_URL`, Supabase, Chroma, Google, and Groq variables in the backend service.
3. Set `CORS_ALLOWED_ORIGINS` to the deployed frontend origin.
4. Run the backend with a production process command such as:

   ```bash
   uvicorn app.backend.router:app --host 0.0.0.0 --port $PORT
   ```

5. Serve `app/frontend` from a static hosting provider.
6. Update the frontend `API_BASE` for the deployed backend URL.
7. Verify `/health`, signup, login, document ingestion, and authenticated queries after deployment.

# working website:

![chatbot demo](screen_shots/deployed_appss/dss3.png)
![chatbot demo](screen_shots/deployed_appss/dss5.png)


## local development:

![chatbot demo](screen_shots/011.png)
![chatbot demo](screen_shots/012.png)
![chatbot demo](screen_shots/013.png)
![chatbot demo](screen_shots/014.png)
![chatbot demo](screen_shots/lstracing.png)
![chatbot demo](screen_shots/fastapi_ss/fa01.png)
![chatbot demo](screen_shots/fastapi_ss/fa02.png)
![chatbot demo](screen_shots/fastapi_ss/fa03.png)
![chatbot demo](screen_shots/fastapi_ss/fa04.png)
![chatbot demo](screen_shots/deployed_appss/dss.png)


## License

See [LICENSE](LICENSE).


## Evaluation

This repository includes reproducible evaluation tooling under `evaluation/`. Metrics are computed from real retrieval/API runs rather than hard-coded values.

Run:
```bash
python evaluation/run_hybrid_eval.py
```

Reported metrics include Hit Rate@K, Recall@K, Precision@K, MRR, and p50/p95 latency where applicable. Results are written to an evaluation results JSON file and should only be used for reporting after running the evaluation against the current system.
