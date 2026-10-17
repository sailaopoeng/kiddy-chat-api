# Kiddy Chat API

A safe and fun FastAPI-based chat application designed specifically for kids! This app integrates with OpenAI and includes comprehensive content filtering to ensure age-appropriate conversations.

## Live Demo
You can try the live demo at [Kiddy Chat API Demo](https://kiddy-chat-api.sailaopoeng.com/docs).

## Features

### Safety Features
- **Content Filtering**: Automatically detects and blocks inappropriate language
- **Age-Appropriate Responses**: System prompts ensure kid-friendly interactions  
- **Dual-Layer Protection**: Input and output filtering for maximum safety
- **Grown-up PIN (optional)**: Only a parent with the PIN can change a session's instructions
- **Rate Limiting**: Each session can send a limited number of messages per minute

### Interactive Features
- **Fun Interface**: Emojis and encouraging language throughout
- **Streaming Replies**: Replies arrive sentence by sentence, already safety-checked
- **Conversation Starters**: Built-in suggestions for fun topics
- **Educational Focus**: Encourages learning, creativity, and positive values
- **Custom Session Prompts**: Frontend can add educational context while maintaining safety

### Core Features
- **Session Management**: Secure sessions with unique IDs
- **Authentication**: Bearer token authentication
- **Chat History**: Maintain conversation context
- **RESTful API**: Clean, documented endpoints
- **Filter Transparency**: View current filters and prompts
- **CORS Support**: Accept requests from any client origin

## Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Environment Setup
Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
UPSTASH_REDIS_REST_URL=your_upstash_redis_rest_url
UPSTASH_REDIS_REST_TOKEN=your_upstash_redis_rest_token
ALLOWED_ORIGINS=*
```

Optional settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `PARENT_PIN` | not set | Turns on the [grown-up PIN](#grown-up-pin). Use 6 or more digits. |
| `PARENT_SIGNING_SECRET` | derived from the PIN and `OPENAI_API_KEY` | Secret used to sign parent approvals. Set a long random string if you prefer not to derive it. |
| `QUERY_RATE_LIMIT_PER_MINUTE` | `20` | Messages allowed per session per minute. `0` turns the limit off. |

`UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are required for durable sessions on Vercel. If they are not set, the app tries `UPSTASH2_KV_REST_API_URL`/`UPSTASH2_KV_REST_API_TOKEN`, then `KV_REST_API_URL`/`KV_REST_API_TOKEN`. If none are set, it uses in-memory sessions (fine for local/Docker/App Runner usage).

### 3. Run Application
```bash
python main.py
```
Visit: `http://localhost:8080/docs` for interactive API documentation.

### 4. Vercel Deployment
This project now supports Vercel's native Python/FastAPI runtime.

1. Create or connect the Vercel project.
2. Add an Upstash Redis database from Vercel Marketplace or Upstash.
3. Configure these Vercel environment variables:
   - `OPENAI_API_KEY`
   - `UPSTASH_REDIS_REST_URL`
   - `UPSTASH_REDIS_REST_TOKEN`
   - `ALLOWED_ORIGINS` (optional, comma-separated; defaults to `*`)
   - `CRON_SECRET` (any long random string; protects `/cron/keepalive`)
   - `PARENT_PIN` (optional; see [Grown-up PIN](#grown-up-pin))
4. Deploy with Vercel.

The Vercel config targets the Singapore region (`sin1`) in `vercel.json` and schedules a daily keep-alive cron (see below). `pyproject.toml` points Vercel at the FastAPI app entrypoint (`main:app`) through `[project.scripts]`, pins Python 3.12, and mirrors the deployment dependencies.

### 5. AWS App Runner Deployment [legacy]
For AWS App Runner deployment, the app is already configured with:
- Docker support (Dockerfile included)
- Python 3.11 compatibility
- Production-ready uvicorn server
- Health checks for AWS App Runner

These files are retained as [legacy] deployment for AWS App Runner and rollback reference:
- `Dockerfile`
- `apprunner.yaml`

### 6. Local Testing with Docker
```bash
# Build the image
docker build -t kiddy-chat-api .

# Run locally (same as AWS App Runner)
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your_key \
  -e UPSTASH_REDIS_REST_URL=your_upstash_url \
  -e UPSTASH_REDIS_REST_TOKEN=your_upstash_token \
  kiddy-chat-api
```

## API Endpoints

### Basic Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check and welcome message |
| POST | `/initiate-session` | Create new chat session |
| POST | `/query` | Send message (requires auth) |
| POST | `/query/stream` | Send message, get the reply as a stream (requires auth) |
| GET | `/session/{id}/history` | Get chat history (requires auth) |
| DELETE | `/session` | End session (requires auth) |

### Helper Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/conversation-starters` | Get fun conversation topics |
| GET | `/filter-info` | Get current filters and prompts |
| GET | `/redoc` | ReDoc API documentation with pinned ReDoc assets |

### Advanced Features

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/session/add-prompt` | Add custom session prompt (requires auth; also the grown-up PIN when enabled) |
| GET | `/session/prompt-info` | Get session prompt details (requires auth) |
| GET | `/parent/status` | Whether the grown-up PIN is enabled |
| POST | `/parent/verify` | Check the PIN and get a 15-minute parent token |

### Streaming Replies

`POST /query/stream` takes the same body as `/query` and returns Server-Sent Events (`text/event-stream`):

```
event: delta
data: {"text": "Octopuses have three hearts!"}

event: delta
data: {"text": " They also have blue blood."}

event: done
data: {"response": "Octopuses have three hearts! They also have blue blood. Cool, right?", "session_id": "...", "username": "emma"}
```

- `delta` events only ever contain **complete sentences that already passed the word filter**, so a child never sees a blocked word, even briefly.
- If the filter catches something later in the reply, streaming stops and `done.response` holds the safe replacement message. Clients should always show `done.response` as the final reply.
- The stream always ends with one `done` event, including when OpenAI fails.

### Grown-up PIN

Without `PARENT_PIN`, anyone holding a session ID (including the child's browser) can change that session's instructions with `/session/add-prompt`.

With `PARENT_PIN` set:

1. The frontend calls `GET /parent/status` → `{"pin_required": true}` and asks the grown-up for the PIN.
2. `POST /parent/verify` with `{"pin": "..."}` returns `{"parent_token": "...", "expires_in": 900}`. A wrong PIN returns 401. After 5 wrong PINs from one address (or 30 in total) verification is locked for 15 minutes (429).
3. `POST /session/add-prompt` with the header `X-Parent-Token: <parent_token>` saves the instructions and returns a `signature` for that exact text.
4. To apply the same instructions to a later session without the PIN, send `{"additional_prompt": "<same text>", "signature": "<signature>"}`. Changed text is rejected with 403.

Changing `PARENT_PIN` (or `PARENT_SIGNING_SECRET` / `OPENAI_API_KEY` when the secret is derived) invalidates earlier signatures, so grown-ups need to save their instructions again.

### Keep-alive Cron

`GET /cron/keepalive` writes a short-lived `keepalive` key to Redis so Upstash does not archive the free database for inactivity. Vercel calls it daily at 03:00 UTC (`crons` in `vercel.json`).

It requires `Authorization: Bearer <CRON_SECRET>`, which Vercel sends automatically when the `CRON_SECRET` environment variable is set. Without a matching header it returns 401. It returns `{"ok": true}` when Redis responds, or HTTP 503 with `{"ok": false}` when it does not, so failed runs show up in the Vercel cron logs.

## Authentication

1. Create session: `POST /initiate-session` → get `session_id`
2. Use as Bearer token: `Authorization: Bearer <session_id>`
3. Without valid session: returns 401 Unauthorized

## Usage Examples

### Basic Flow
```bash
# 1. Create session
curl -X POST "http://localhost:8080/initiate-session" 
     -H "Content-Type: application/json" 
     -d '{"username": "emma"}'

# 2. Send message
curl -X POST "http://localhost:8080/query" 
     -H "Authorization: Bearer <SESSION_ID>" 
     -H "Content-Type: application/json" 
     -d '{"message": "Tell me about dinosaurs!"}'

# 3. Add custom educational prompt
curl -X POST "http://localhost:8080/session/add-prompt" 
     -H "Authorization: Bearer <SESSION_ID>" 
     -H "Content-Type: application/json" 
     -d '{"additional_prompt": "Act like a friendly science teacher"}'
```

### Frontend Integration
```javascript
// Create session
const response = await fetch('/initiate-session', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'emma' })
});
const { session_id } = await response.json();

// Send message
const chatResponse = await fetch('/query', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${session_id}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ message: 'What is gravity?' })
});
```

## Safety System

### Content Filtering
Automatically blocks:
- Inappropriate language and words
- Violent or scary content  
- Adult topics
- Negative or harmful speech patterns

### Safety Response
When inappropriate content is detected:
1. Block content from reaching AI
2. Respond with gentle, educational message
3. Redirect to positive topics
4. Log for monitoring

### AI Configuration
- **Model**: set by `OPENAI_MODEL` in `main.py`
- **Max Completion Tokens**: 1000 (includes reasoning tokens; reply length is kept short by the system prompt)
- **Moderation**: Dual-layer filtering

### AWS Secrets Manager Support
- **Flexible API Key Format**: Supports both plain text and JSON formats
- **Automatic Detection**: Intelligently parses the secret format
- **Production Ready**: Seamless integration with AWS infrastructure
- **Enhanced Logging**: Detailed format detection and parsing logs

The application automatically handles OpenAI API keys from AWS Secrets Manager in either format:
- Plain text: `sk-1234567890abcdef...`
- JSON: `{"OPENAI_API_KEY": "sk-1234567890abcdef..."}`

### Custom Prompts
- **Additive Only**: Never replaces safety prompts
- **Session Scoped**: Per-session customization
- **Safety Preserved**: All filtering remains active
- **Educational**: Perfect for tutoring contexts

## Session Storage

Sessions are stored in Upstash Redis when these environment variables are configured:

```env
UPSTASH_REDIS_REST_URL=your_upstash_redis_rest_url
UPSTASH_REDIS_REST_TOKEN=your_upstash_redis_rest_token
```

Each session is stored as `session:{session_id}` with a 24-hour TTL. Active session IDs are tracked in `sessions:index` so `/sessions/active` can count sessions without scanning every key.

If Upstash is not configured, or a Redis call fails or takes longer than 3 seconds, the app logs a warning and uses an in-memory session store with the same 24-hour expiry. After a failure it skips Redis for 60 seconds, so requests don't keep waiting on a dead database, then tries again. Redis errors never turn into a 500.

`GET /` reports the current mode as `"session_store": "redis"` or `"memory"`.

Memory mode is a fallback only: sessions are lost when an instance cold starts and are not shared between instances, so a user may need to start a new session.

### Redis Data Purge

Session data is temporary and can be purged safely when you need to reset the environment.

Dry run:

```bash
python scripts/purge_redis_sessions.py
```

Delete all `session:*` keys and `sessions:index`:

```bash
python scripts/purge_redis_sessions.py --confirm
```

The purge script reads the same Redis environment variables as the app. No public HTTP purge endpoint is exposed.

## Project Structure

```
gpt-for-kids-backend/
|-- main.py                         # FastAPI application
|-- requirements.txt                # Dependencies
|-- pyproject.toml                  # Vercel Python runtime config
|-- vercel.json                     # Vercel region and cron config
|-- scripts/purge_redis_sessions.py # Redis session purge utility
|-- tests/                          # pytest tests (fake OpenAI client)
|-- requirements-dev.txt            # Test dependencies
|-- Dockerfile                      # Legacy App Runner/container config
|-- apprunner.yaml                  # Legacy App Runner config
`-- README.md                       # Documentation
```

## 🔧 Error Handling

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid input (empty username/message) |
| 401 | Invalid or missing session ID, or wrong grown-up PIN |
| 403 | Instructions change without grown-up approval (PIN enabled) |
| 404 | `/parent/verify` when no PIN is configured |
| 422 | Request too large (username over 50, message or instructions over 2000 characters) |
| 429 | Too many messages for this session, or too many wrong PINs |
| 500 | OpenAI API or server errors |

## Security

- **Sessions**: Upstash Redis storage with 24-hour expiration on Vercel
- **API Keys**: Secure storage, never commit to version control
- **Errors**: Client error messages are generic; exception details stay in server logs
- **Cron**: `/cron/keepalive` is protected by `CRON_SECRET`

- **Rate limits**: per-session message limit and PIN lockout use Redis when available, so they are shared by all instances; in memory mode they apply per instance
- **Grown-up PIN**: compared in constant time; parent tokens and approved instructions are HMAC-signed

## Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
```

The tests use a fake OpenAI client and in-memory sessions, so they need no API key or network. GitHub Actions runs them on every push and pull request.

## License

MIT License
