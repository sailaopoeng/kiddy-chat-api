# Kiddy Chat API

A safe and fun FastAPI-based chat application designed specifically for kids! This app integrates with OpenAI's GPT-4o-mini model and includes comprehensive content filtering to ensure age-appropriate conversations.

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

## Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Environment Setup
Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_secret_key_here
```

### 3. Run Application
```bash
python main.py
```
Visit: `http://localhost:8080/docs` for interactive API documentation.

### 4. AWS App Runner Deployment
For AWS App Runner deployment, the app is already configured with:
- Docker support (Dockerfile included)
- Python 3.11 compatibility
- Production-ready uvicorn server
- Health checks for AWS App Runner

### 5. Local Testing with Docker
```bash
# Build the image
docker build -t kiddy-chat-api .

# Run locally (same as AWS App Runner)
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your_key \
  -e SECRET_KEY=your_secret \
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

### Custom Prompts
- **Additive Only**: Never replaces safety prompts
- **Session Scoped**: Per-session customization
- **Safety Preserved**: All filtering remains active
- **Educational**: Perfect for tutoring contexts

## Project Structure

```
gpt-for-kids-backend/
├── main.py              # FastAPI application
├── requirements.txt     # Dependencies  
├── .env                # Environment variables
├── Dockerfile          # Container config
└── README.md           # Documentation
```

## 🔧 Error Handling

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid input (empty username/message) |
| 401 | Invalid or missing session ID |
| 500 | OpenAI API or server errors |

## Security

- **Sessions**: In-memory storage, 24-hour expiration
- **API Keys**: Secure storage, never commit to version control

**TODO**: :
   - Using Redis or a database for session storage
   - Implementing rate limiting
   - Using proper secret management

## License

MIT License