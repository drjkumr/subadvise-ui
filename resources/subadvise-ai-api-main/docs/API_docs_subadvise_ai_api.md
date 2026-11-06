# SubAdvise AI API Reference

This document describes the FastAPI service in `subadvise-ai-api`. The service
proxies the GET endpoints, subscription PATCH endpoint, and expense
creation/configuration endpoints of the Java `subadvise-api` and provides a
Groq-powered assistant whose tools dispatch through the existing FastAPI
handlers in `controller/routes.py`.

## Configuration

| Environment variable | Default | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | None | Required Groq credential. The application fails during startup if it is missing or blank. |
| `SUBADVISE_API_BASE_URL` | `http://localhost:7071` | Origin of the Java API. Set the origin only; do not add `/api`. |
| `CHAT_HISTORY_DIR` | `<project>/data/chat_history` | Directory containing one JSON file per chat session. |
| `CHAT_VECTOR_DIR` | `<project>/data/chroma_db` | Persistent local ChromaDB directory. |

The assistant uses Groq's OpenAI-compatible API at
`https://api.groq.com/openai/v1` with model `openai/gpt-oss-120b`.

### Start on Windows

On Windows, use Python 3.14 x64. Python 3.15 does not currently have a
compatible ONNX Runtime wheel, which ChromaDB's default embedding function
requires. From this directory, set the required key and start the API:

```powershell
$env:GROQ_API_KEY = "<your Groq API key>"
$env:SUBADVISE_API_BASE_URL = "http://localhost:7071"
py -3.14 -m pip install -r requirements.txt
py -3.14 -m uvicorn main:app --host 0.0.0.0 --port 7072
```

The API documentation UI is available at `/docs` and the OpenAPI document at
`/openapi.json` on the FastAPI server.

## Endpoint summary

| Method | FastAPI path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check that the API is running. |
| `POST` | `/api/assistant/chat` | Ask a question or stage a confirmed subscription/expense change. |
| `POST` | `/api/assistant/sessions` | Create an empty chat session. |
| `GET` | `/api/assistant/sessions/{session_id}` | Retrieve a session and its complete ordered message history. |
| `DELETE` | `/api/assistant/sessions/{session_id}/history` | Clear a session's JSON transcript while retaining its semantic context. |
| `DELETE` | `/api/assistant/sessions/{session_id}/context` | Clear a session's semantic context while retaining its JSON transcript. |
| `DELETE` | `/api/assistant/sessions/{session_id}/memory` | Clear both a session's JSON transcript and semantic context. |
| `GET` | `/api/assistant/history/search` | Semantically search indexed history, optionally within a session. |
| `PUT` | `/api/settings/groq-api-key` | Replace the in-memory Groq key; requires the current key as a bearer token. |
| `GET` | `/api/subscriptions` | Get all subscriptions. |
| `GET` | `/api/subscriptions/search?name=netflix` | Search subscription names by case-insensitive substring. |
| `GET` | `/api/subscriptions/{subscription_id}` | Get a subscription by UUID. |
| `PATCH` | `/api/subscriptions/{subscription_id}` | Partially update a subscription. |
| `GET` | `/api/subscriptions/filter/subscription-date` | Filter by exact subscription date. |
| `GET` | `/api/subscriptions/filter/renewal-date` | Filter by exact renewal date. |
| `GET` | `/api/subscriptions/filter/renewal-range` | Filter by renewal date range. |
| `GET` | `/api/subscriptions/filter/subscription-range` | Filter by subscription date range. |
| `GET` | `/api/currency/convert` | Convert a currency amount using the Java API. |
| `GET` | `/api/expenses/monthly` | Get the monthly expenses report. |
| `GET` | `/api/expenses/color-thresholds` | Get configured expense color thresholds. |
| `POST` | `/api/expenses/targets` | Create an expense target. |
| `POST` | `/api/expenses` | Record an actual expense. |
| `PUT` | `/api/expenses/color-thresholds` | Update expense color thresholds. |

The proxy routes forward requests to the matching Java API path. The assistant
can stage subscription and expense changes, but the user must send a separate
`confirm update` message before a staged change is sent upstream. `cancel
update` discards the proposal. Pending proposals are held in process memory and
are discarded if the service restarts.

The assistant does not make HTTP requests directly to the Java API. When Groq
selects a tool, the application dispatches it to the corresponding existing
route handler in `controller/routes.py`. That handler validates and forwards the
request using the same proxy client logic as the public API routes.

## Persistent chat memory

Each chat session has two local persistence layers:

- **JSON history:** one `<session_id>.json` file per session, containing the
  complete ordered message history and session metadata. Updates are written to
  a temporary file and atomically replace the previous session file.
- **ChromaDB vector index:** messages are embedded and stored in the persistent
  local collection `subadvise_chat_history`, with session, role, timestamp, and
  message ID metadata. The default Chroma embedding function may download its
  embedding model the first time a message is indexed.

The JSON store is the source of truth for full session history. Each appended
message is saved to JSON and then upserted into ChromaDB using its stable message
ID. If indexing fails, the error is surfaced; the JSON message remains
persisted. Keep both directories on persistent storage and protect them because
they contain conversation content. `HybridChatMemory.reindex_history()` can
re-upsert JSON-persisted messages into ChromaDB after repairing or recreating
the vector collection.

### `POST /api/assistant/sessions`

Create an empty session before starting a conversation. Session metadata is
optional and accepts JSON scalar values.

Request:

```json
{
  "metadata": {
    "client": "web"
  }
}
```

Response (`201 Created`):

```json
{
  "session_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
  "created_at": "2026-10-22T05:30:00Z"
}
```

### Chat session IDs

`POST /api/assistant/chat` accepts an optional `session_id` alongside the
message. If it is omitted, the service creates a new session:

```json
{
  "message": "Which subscriptions renew soon?"
}
```

The response includes the session ID; clients should send it on subsequent chat
requests to continue the same conversation:

```json
{
  "session_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
  "response": "..."
}
```

Each user message is stored before the Groq request; each successful assistant
answer is stored after generation. The assistant receives the last six user /
assistant turns from JSON history and up to five semantically relevant older
messages from the same session. Recent messages are not duplicated in retrieved
context. Tool-call payloads are not persisted as conversation messages.
Storage/index failures return `503 Service Unavailable`; an unknown supplied
session ID returns `404 Not Found`.

Example response:

```json
{
  "session_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
  "response": "..."
}
```

### `GET /api/assistant/sessions/{session_id}`

Returns session metadata and every stored message in order. Returns
`404 Not Found` if the session does not exist.

### Clear a session's history, context, or both

These manual endpoints operate on one existing session and leave the session
itself and its metadata intact. They are API routes only and are not available
as assistant tools. They do not require bearer authentication; protect them
with the same network controls as the other unauthenticated API routes.

- `DELETE /api/assistant/sessions/{session_id}/history` clears the JSON
  transcript. Semantic context remains indexed and searchable.
- `DELETE /api/assistant/sessions/{session_id}/context` removes that session's
  entries from ChromaDB. The JSON transcript remains available to the
  assistant's recent-history logic.
- `DELETE /api/assistant/sessions/{session_id}/memory` clears both stores.

Each route returns the number of records removed from each store. For example:

```json
{
  "session_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
  "messages_deleted": 12,
  "context_items_deleted": 12
}
```

Clearing an already-empty store succeeds with a count of `0`. An unknown
session returns `404 Not Found`; storage failures return `503 Service
Unavailable`.

### `GET /api/assistant/history/search`

Searches semantically indexed messages across sessions or within one session.

| Parameter | Location | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `query` | Query | String (1–4,000 chars) | Yes | Text used for semantic search. |
| `session_id` | Query | UUID | No | Restrict results to one session. |
| `top_k` | Query | Integer (1–50) | No | Maximum number of matches; defaults to 5. |

Example:
`/api/assistant/history/search?query=annual%20subscription&top_k=5`

Response:

```json
{
  "results": [
    {
      "message": {
        "message_id": "123e4567-e89b-12d3-a456-426614174000",
        "session_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
        "role": "user",
        "content": "I pay for an annual music subscription.",
        "timestamp": "2026-10-22T05:30:00Z",
        "metadata": {}
      },
      "distance": 0.18
    }
  ]
}
```

An empty collection or no session matches returns `{"results":[]}`. Storage or
vector query failures return `503 Service Unavailable`.

## Assistant

### `POST /api/assistant/chat`

Ask a natural-language question about subscriptions, renewal dates, currency
conversion, or expenses. Groq may select read tools or stage a subscription or
expense change when explicitly requested. The application executes tools by
calling the corresponding FastAPI route handlers in `controller/routes.py`,
then returns the model's answer. A staged change is not applied until the user
confirms it in a separate chat message by replying exactly `confirm update`;
`cancel update` discards it.

Request:

```json
{
  "session_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
  "message": "Which subscriptions renew in December 2026?"
}
```

Response:

```json
{
  "session_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
  "response": "..."
}
```

`message` is required and must contain 1–12,000 characters.

Responses:

| Status | Meaning |
| --- | --- |
| `200 OK` | Assistant returned an answer. |
| `404 Not Found` | The requested session ID does not exist. |
| `503 Service Unavailable` | Chat JSON or vector memory storage failed. |
| `422 Unprocessable Entity` | Request body is invalid or `message` is outside its allowed length. |
| `502 Bad Gateway` | Groq API request failed or the assistant exceeded its tool-call limit. |
| `504 Gateway Timeout` | Groq API request timed out. |

An upstream Java API error encountered during a tool call is returned to the
model as tool data; the assistant may describe the error in its `200` response.
For the exact upstream status and response body, call the corresponding proxy
endpoint directly.

The application makes at most six successive Groq tool-call rounds per
question. SubAdvise tool calls have a 15-second HTTP timeout; each Groq request
has a 600-second timeout.

### `PATCH /api/subscriptions/{subscription_id}`

Partially updates an existing subscription through the Java API. The body may
include one or more of `subscriptionName`, `subscriptionDate`, `renewalDate`,
`subscriptionPrice`, and `currency`. The assistant does not call this operation
until the user confirms a staged update in the same chat session.

Example:

```json
{
  "subscriptionName": "Spotify"
}
```

## Groq API key rotation

### `PUT /api/settings/groq-api-key`

Replaces the key used by subsequent assistant requests. Send the currently
active key in the `Authorization` header using the `Bearer` authentication
scheme. The JSON body contains the replacement key:

```json
{
  "api_key": "<replacement Groq API key>"
}
```

Success response:

```json
{
  "message": "Groq API key updated."
}
```

The response never includes the key. `api_key` must contain 1–512 characters;
surrounding whitespace is removed before storing it.

| Status | Meaning |
| --- | --- |
| `200 OK` | Key was replaced in this process. |
| `401 Unauthorized` | The bearer token is missing or is not the current key. |
| `422 Unprocessable Entity` | Request body is invalid, or the key is blank/too long. |

Rotation is in-memory and is not persisted. Update `GROQ_API_KEY` in the
deployment environment to keep the replacement after restart. With multiple
worker processes, each worker has separate in-memory state; use one worker for
in-process key rotation, or redeploy workers with the replacement environment
variable.

PowerShell example, assuming the current and replacement keys are available as
environment variables:

```powershell
$headers = @{ Authorization = "Bearer $env:GROQ_CURRENT_API_KEY" }
$body = @{ api_key = $env:GROQ_NEW_API_KEY } | ConvertTo-Json
Invoke-RestMethod `
  -Method Put `
  -Uri "http://localhost:7072/api/settings/groq-api-key" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

## Read-only SubAdvise GET endpoints

All dates use ISO format `YYYY-MM-DD`. Query parameter names and capitalization
match the Java API.

### Subscriptions

#### `GET /api/subscriptions`

Returns all saved subscriptions.

#### `GET /api/subscriptions/search`

Searches saved subscriptions by a case-insensitive name fragment. The required
`name` query parameter must contain non-whitespace text. No matches return an
empty list.

| Parameter | Location | Type | Required |
| --- | --- | --- | --- |
| `name` | Query | String | Yes |

Example: `/api/subscriptions/search?name=netflix`

The assistant can perform the same search when answering subscription
questions.

#### `GET /api/subscriptions/{subscription_id}`

Returns one subscription.

| Parameter | Location | Type | Description |
| --- | --- | --- | --- |
| `subscription_id` | Path | UUID | Subscription identifier. |

The Java API returns `404 Not Found` when the ID does not exist.

#### `GET /api/subscriptions/filter/subscription-date`

Filters subscriptions by their exact subscription date.

| Parameter | Location | Type | Required |
| --- | --- | --- | --- |
| `date` | Query | Date (`YYYY-MM-DD`) | Yes |

Example: `/api/subscriptions/filter/subscription-date?date=2026-06-01`

#### `GET /api/subscriptions/filter/renewal-date`

Filters subscriptions by their exact renewal date.

| Parameter | Location | Type | Required |
| --- | --- | --- | --- |
| `date` | Query | Date (`YYYY-MM-DD`) | Yes |

Example: `/api/subscriptions/filter/renewal-date?date=2027-06-01`

#### `GET /api/subscriptions/filter/renewal-range`

Filters subscriptions by renewal date within the supplied range.

| Parameter | Location | Type | Required |
| --- | --- | --- | --- |
| `startDate` | Query | Date (`YYYY-MM-DD`) | Yes |
| `endDate` | Query | Date (`YYYY-MM-DD`) | Yes |

Example:
`/api/subscriptions/filter/renewal-range?startDate=2026-01-01&endDate=2026-12-31`

#### `GET /api/subscriptions/filter/subscription-range`

Filters subscriptions by subscription date within the supplied range.

| Parameter | Location | Type | Required |
| --- | --- | --- | --- |
| `startDate` | Query | Date (`YYYY-MM-DD`) | Yes |
| `endDate` | Query | Date (`YYYY-MM-DD`) | Yes |

Example:
`/api/subscriptions/filter/subscription-range?startDate=2026-01-01&endDate=2026-06-30`

### Currency

#### `GET /api/currency/convert`

Converts an amount using the Java API's latest available exchange-rate
snapshot.

| Parameter | Location | Type | Validation |
| --- | --- | --- | --- |
| `amount` | Query | Decimal | Must be zero or greater. |
| `from` | Query | Currency code | Required; three-letter ISO 4217 code accepted by the Java API. |
| `to` | Query | Currency code | Required; three-letter ISO 4217 code accepted by the Java API. |

Example: `/api/currency/convert?amount=100&from=USD&to=EUR`

The Java API can return `400` for malformed parameters or a negative amount,
`422` when a valid currency code has no provider rate, and `503` when rates are
unavailable. Exchange rates may be cached until the provider's next update;
they are not real-time. Retain the ExchangeRate-API attribution included in
conversion responses when displaying converted amounts.

### Expenses

#### `GET /api/expenses/monthly`

Returns the monthly expense report grouped by currency, including the color
classification for each expense.

| Parameter | Location | Type | Validation |
| --- | --- | --- | --- |
| `year` | Query | Integer | Required. |
| `month` | Query | Integer | Required; 1–12. |

Example: `/api/expenses/monthly?year=2026&month=2`

The Java API groups totals by currency and uses each target's end date to
determine the month.

#### `GET /api/expenses/color-thresholds`

Returns the configured application-wide expense color thresholds.

### `POST /api/expenses/targets`

Creates an expense target. Required JSON fields are `targetExpense`,
`currency`, and `endDate`; `startDate` is optional. Assistant-created targets
are staged and require a separate `confirm update` chat message before saving.

### `POST /api/expenses`

Records an actual expense against an existing target. Required JSON fields are
`actualExpense`, `currency`, and `targetId`. The currency must match the
target's currency. Assistant-created expenses require confirmation before
recording.

### `PUT /api/expenses/color-thresholds`

Replaces the application-wide `red`, `orange`, `yellow`, `lime`, and `green`
minimum percentage thresholds. Each value must be from 0 to 100 and thresholds
must strictly descend in that order. Assistant-initiated changes require
confirmation before saving.

## Proxy behavior and errors

- Java API response status codes, bodies, and content types are passed through
  by the proxy routes.
- `502 Bad Gateway` indicates the Java API could not be reached.
- `504 Gateway Timeout` indicates the Java API request timed out.
- Invalid FastAPI query parameters (for example, an invalid UUID/date or a
  month outside 1–12) return `422 Unprocessable Entity` before proxying.
- Invalid PATCH, POST, and PUT bodies return `422 Unprocessable Entity` before
  proxying.
- The Java API's own error status is otherwise preserved by the proxy routes.

## Security considerations

- The chat and data endpoints, including subscription and expense writes, do not have
  application-level authentication. Assistant-driven updates require an
  explicit confirmation message, but this is not a substitute for
  authentication. Restrict network access or place the service behind an
  authentication layer before making it remotely accessible.
- Bind to localhost for local development. Use HTTPS for remote access; the
  bearer token and request body both contain credentials during key rotation.
- Do not commit API keys, put real keys in documentation, or log request
  bodies/`Authorization` headers. Prefer a secret manager or protected
  environment configuration over shell history for production secrets.
- Anyone with the current Groq key can rotate it through the key-management
  route. Restrict access to that route at the network or gateway level too.
