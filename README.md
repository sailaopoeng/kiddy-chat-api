# Kiddy Chat API

A safe and fun FastAPI-based chat application designed specifically for kids! This app integrates with OpenAI's GPT-4o-mini model and includes comprehensive content filtering to ensure age-appropriate conversations.

## Live Demo
You can try the live demo at [Kiddy Chat API Demo](https://kiddy-chat-api.sailaopoeng.com/docs).

## Features

### Safety Features
- **Content Filtering**: Automatically detects and blocks inappropriate language
- **Age-Appropriate Responses**: System prompts ensure kid-friendly interactions  
- **Safe AI Model**: Uses GPT-4o-mini with reduced temperature for consistent responses
- **Dual-Layer Protection**: Input and output filtering for maximum safety

### Interactive Features
- **Fun Interface**: Emojis and encouraging language throughout
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

`UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are required for durable sessions on Vercel. If they are absent, the app falls back to in-memory sessions for legacy local/Docker/App Runner usage.

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
   - `ENABLE_DEBUG_ENDPOINTS` (optional; keep unset in production)
4. Deploy with Vercel.

The Vercel config targets the Singapore region (`sin1`) in `vercel.json`. `pyproject.toml` points Vercel at the FastAPI app entrypoint (`main:app`) through `[project.scripts]`, pins Python 3.12, and mirrors the deployment dependencies.

### 5. AWS App Runner Deployment History
For AWS App Runner deployment, the app is already configured with:
- Docker support (Dockerfile included)
- Python 3.11 compatibility
- Production-ready uvicorn server
- Health checks for AWS App Runner

These files are retained as deployment history and rollback reference:
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
| GET | `/session/{id}/history` | Get chat history (requires auth) |
| DELETE | `/session` | End session (requires auth) |

### Helper Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/conversation-starters` | Get fun conversation topics |
| GET | `/filter-info` | Get current filters and prompts |

### Advanced Features

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/session/add-prompt` | Add custom session prompt (requires auth) |
| GET | `/session/prompt-info` | Get session prompt details (requires auth) |

### Debug Endpoints

`GET /debug/env-check` is disabled by default and returns 404. Enable it only for temporary troubleshooting by setting:

```env
ENABLE_DEBUG_ENDPOINTS=true
```

The endpoint reports configuration status only and does not return API key previews.

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
- **Model**: GPT-4o-mini
- **Temperature**: 0.5 (consistent responses)
- **Max Tokens**: 300 (appropriate length)
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

If Upstash is not configured, the app uses in-memory session storage as a legacy fallback. That fallback is not reliable on Vercel because serverless instances can cold start or scale independently.

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

The purge script requires `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` in the environment. No public HTTP purge endpoint is exposed.

## Project Structure

```
gpt-for-kids-backend/
|-- main.py                         # FastAPI application
|-- requirements.txt                # Dependencies
|-- pyproject.toml                  # Vercel Python runtime config
|-- vercel.json                     # Vercel region config
|-- scripts/purge_redis_sessions.py # Redis session purge utility
|-- Dockerfile                      # Legacy App Runner/container config
|-- apprunner.yaml                  # Legacy App Runner config
`-- README.md                       # Documentation
```

## 🔧 Error Handling

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid input (empty username/message) |
| 401 | Invalid or missing session ID |
| 500 | OpenAI API or server errors |

## Security

- **Sessions**: Upstash Redis storage with 24-hour expiration on Vercel
- **API Keys**: Secure storage, never commit to version control
- **Debugging**: Debug environment endpoint disabled by default

**TODO**: :
   - Implementing rate limiting

## License

MIT License
