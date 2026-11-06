# SubAdvise AI API

A FastAPI service that provides:

- A proxy for the documented GET endpoints, subscription PATCH operation, and
  expense creation/configuration endpoints in `subadvise-api`.
- A Groq-powered assistant using `openai/gpt-oss-120b`, with account-data
  lookup and confirmation-gated subscription and expense changes through
  existing FastAPI route handlers.
- Persistent chat sessions: complete JSON history plus ChromaDB semantic
  retrieval for older messages.
- An authenticated endpoint for rotating the Groq API key while the service is
  running.

See the [SubAdvise AI API reference](docs/API_docs_subadvise_ai_api.md) for
the complete route contracts, examples, errors, and security notes.

## Configuration and storage

| Setting | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | Required | Groq credential. Startup fails if this is missing or blank. |
| `SUBADVISE_API_BASE_URL` | `http://localhost:7071` | Java API origin. Do not append `/api`. |
| `CHAT_HISTORY_DIR` | `data/chat_history` | JSON session files. |
| `CHAT_VECTOR_DIR` | `data/chroma_db` | Persistent ChromaDB index. |

Conversation JSON files and the local ChromaDB index are stored under
`data/chat_history` and `data/chroma_db` inside this project by default. Set
`CHAT_HISTORY_DIR` and `CHAT_VECTOR_DIR` to use different persistent locations.
JSON is the source of truth for full transcripts; each message is also indexed
in ChromaDB for semantic recall. ChromaDB's default embedding function uses the
`all-MiniLM-L6-v2` sentence-transformer model to turn messages and search
queries into vectors. The model may be downloaded the first time a message is
indexed, so the first indexing request can take longer and needs network access.

Embedding and vector search are local workloads: a capable, multi-core CPU and
enough memory help keep indexing and searches responsive, especially under
multiple concurrent requests. A GPU or NPU can help only when the installed
embedding runtime and drivers support it and the application is configured to
use that accelerator; the current default ChromaDB setup does not enable GPU or
NPU acceleration automatically. Keep both data directories on persistent,
access-controlled storage because they contain conversation content.

## Get a Groq API key

Create an API key at [Groq Console](https://console.groq.com/keys) before
starting the application. Set it as the `GROQ_API_KEY` environment variable
for local runs and before building the Docker image. Do not commit the key or
put it in the Dockerfile; Compose passes it to the running container.

## Run locally

Run these commands from the project directory. Python 3.14 is recommended.
On Windows, use Python 3.14 x64 because ChromaDB requires a compatible ONNX
Runtime wheel.

### macOS and Linux

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export GROQ_API_KEY="<your Groq API key>"
# Optional; defaults to http://localhost:7071.
export SUBADVISE_API_BASE_URL="http://localhost:7071"
python -m uvicorn main:app --host 0.0.0.0 --port 7072
```

### Windows PowerShell

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:GROQ_API_KEY = "<your Groq API key>"
# Optional; defaults to http://localhost:7071.
$env:SUBADVISE_API_BASE_URL = "http://localhost:7071"
python -m uvicorn main:app --host 0.0.0.0 --port 7072
```

## Run with Docker

Requires Docker Engine and Docker Compose v2. Get a Groq API key first, then
set `GROQ_API_KEY` in the same shell before building the image; Compose requires
it and passes it to the container when it starts.

### macOS and Linux

```sh
export GROQ_API_KEY="<your Groq API key>"
docker compose build
docker compose up -d
```

### Windows PowerShell

```powershell
$env:GROQ_API_KEY = "<your Groq API key>"
docker compose build
docker compose up -d
```

Compose publishes the API on port `7072` and persists chat history and the
ChromaDB index in named volumes. The default upstream URL is
`http://host.docker.internal:7071` for a Java API running on the host. Set
`SUBADVISE_API_BASE_URL` before running Compose to use a different API origin,
such as a service name on a shared Docker network. Do not append `/api` to the
base URL.

Open `http://localhost:7072/docs` for the interactive API documentation. Stop
the service with `docker compose down`; the named data volumes are retained.

## Chat sessions

Create a session or let the first chat request create one:

```powershell
$session = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:7072/api/assistant/sessions" `
  -ContentType "application/json" `
  -Body "{}"

$body = @{
  session_id = $session.session_id
  message = "Which subscriptions renew soon?"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:7072/api/assistant/chat" `
  -ContentType "application/json" `
  -Body $body
```

Keep the returned `session_id` and submit it with subsequent chat requests to
continue the same conversation. The assistant receives the latest six user /
assistant turns plus up to five semantically relevant older messages from that
session. Retrieve the full transcript with
`GET /api/assistant/sessions/{session_id}`. Search indexed history with
`GET /api/assistant/history/search?query=annual%20subscription&top_k=5`;
optionally add `session_id` to limit results to one session.

To run the standalone memory example from this directory:

```powershell
py -3.14 -m examples.chat_memory_demo
```

The example writes separate demo data under `data\demo_chat_history` and
`data\demo_chroma_db`.

## API overview

- `GET /api/health` — check that the API is running.
- `POST /api/assistant/chat` — ask the Groq `openai/gpt-oss-120b` assistant.
- `POST /api/assistant/sessions` — create a chat session.
- `GET /api/assistant/sessions/{session_id}` — retrieve the full session.
- `DELETE /api/assistant/sessions/{session_id}/history` — clear the JSON
  transcript while retaining semantic context.
- `DELETE /api/assistant/sessions/{session_id}/context` — clear semantic
  context while retaining the JSON transcript.
- `DELETE /api/assistant/sessions/{session_id}/memory` — clear both the
  transcript and semantic context.
- `GET /api/assistant/history/search` — semantic search across chat history.
- `PUT /api/settings/groq-api-key` — rotate the active key; requires the
  current key as a bearer token.
- `PATCH /api/subscriptions/{subscription_id}` — partially update a
  subscription; assistant-initiated changes require confirmation.
- `GET /api/subscriptions/search?name=netflix` — search subscriptions by a
  case-insensitive name fragment; also available to the assistant.
- `POST /api/expenses/targets` and `POST /api/expenses` — create a target
  expense or record an actual expense; assistant-initiated changes require
  confirmation.
- `PUT /api/expenses/color-thresholds` — update expense color thresholds;
  assistant-initiated changes require confirmation.
- Subscription, currency, and expense proxy endpoint contracts are listed in
  the API reference.

## Security

The API-key rotation route is authenticated with the currently configured Groq
key. The chat, manual chat-clear, and data-proxy routes, including subscription
and expense changes, do not have application-level authentication.
Assistant-driven changes require a separate `confirm update` message, but this
is not a substitute for API authentication.
Keep the service bound to localhost for local use; before
remote access, put it behind HTTPS and an authentication layer. Do not expose
the service directly to an untrusted network. Avoid entering real keys in
shared shell history; use protected environment configuration or a secret
manager for deployments.

The rotated key is stored in process memory only. Set `GROQ_API_KEY` to the
replacement key in the service environment as well, or the old key will be
loaded on restart. See the API reference for the rotation request and detailed
credential-handling guidance.

Assistant tool calls are dispatched to the handlers in
`controller/routes.py`; the model does not issue HTTP requests to the Java API
or bypass those routes.
