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
- Python 3.9 compatibility
- Production-ready Gunicorn server
- Health checks for AWS App Runner

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
- **Production**: Consider Redis, rate limiting, HTTPS, secret management

## License

MIT License

## 🚀 Quick Start

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

### 3. Run the Application
```bash
python main.py
```

Visit `http://localhost:8080/docs` for interactive API documentation.

## 📚 API Reference

### Core Endpoints

#### 1. Health Check
**GET** `/`
```json
{
    "message": "Welcome to Kiddy Chat API! 🌟 A safe and fun place to chat with AI! 🤖",
    "status": "Ready for awesome conversations!",
    "version": "1.0.0"
}
```

#### 2. Create Session
**POST** `/initiate-session`
```json
// Request
{ "username": "emma" }

// Response
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Session created successfully for emma",
    "username": "emma"
}
```

#### 3. Send Message
**POST** `/query`
```bash
Authorization: Bearer <session_id>
```
```json
// Request
{ "message": "What's your favorite animal?" }

// Response
{
    "response": "I love learning about all animals! 🐾 Dolphins are really cool...",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "emma"
}
```

#### 4. Get Chat History
**GET** `/session/{session_id}/history`
```bash
Authorization: Bearer <session_id>
```

#### 5. End Session
**DELETE** `/session`
```bash
Authorization: Bearer <session_id>
```

### Helper Endpoints

#### 6. Conversation Starters
**GET** `/conversation-starters`
```json
{
    "conversation_starters": [
        "What's your favorite animal and why? 🐾",
        "If you could have any superpower, what would it be? 🦸‍♂️",
        "What's the coolest thing you learned today? 📚"
    ],
    "message": "Here are some fun things we can chat about! 🌟"
}
```

### Advanced Endpoints

#### 7. Get Filter Information
**GET** `/filter-info`
```json
{
    "Additive Only": ["stupid", "idiot", "hate", "kill", "..."],
    "inappropriate_patterns": ["\b(i hate|you suck|go away|shut up)\b", "..."],
    "kids_friendly_responses": [
        "I can't help with that kind of talk. Let's use kind words instead! 😊"
    ],
    "default_system_prompt": "You are a helpful, friendly, and safe AI assistant..."
}
```

#### 8. Add Custom Session Prompt
**POST** `/session/add-prompt`
```bash
Authorization: Bearer <session_id>
```
```json
// Request
{
    "additional_prompt": "Please respond like a friendly science teacher who loves to explain things with simple experiments."
}

// Response
{
    "message": "Additional prompt added successfully! This will guide our conversation while keeping all safety features active.",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "additional_prompt": "Please respond like a friendly science teacher..."
}
```

#### 9. Get Session Prompt Info
**GET** `/session/prompt-info`
```bash
Authorization: Bearer <session_id>
```
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "emma",
    "default_system_prompt": "You are a helpful, friendly, and safe AI assistant...",
    "additional_prompt": "Please respond like a friendly science teacher...",
    "combined_system_message": "Combined prompt...",
    "created_at": "2024-01-15T10:30:00"
}
```

## 🎯 Authentication

1. **Create a session** using `/initiate-session`
2. **Use the returned session_id** as a Bearer token
3. **Include in header**: `Authorization: Bearer <session_id>`
4. **Without valid session ID**: `/query` returns 401 Unauthorized

## 💻 Usage Examples

### Frontend Integration (JavaScript)
```javascript
// Get filter information for frontend display
fetch('/filter-info')
  .then(response => response.json())
  .then(data => {
    console.log('Filtered words:', data.inappropriate_words);
    console.log('System prompt:', data.default_system_prompt);
  });

// Add session-specific instructions  
fetch('/session/add-prompt', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${sessionId}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    additional_prompt: 'Please focus on math topics and use simple examples'
  })
});

// Check current session configuration
fetch('/session/prompt-info', {
  headers: { 'Authorization': `Bearer ${sessionId}` }
})
.then(response => response.json())
.then(data => {
  console.log('Additional prompt:', data.additional_prompt);
  console.log('Combined prompt:', data.combined_system_message);
});
```

### cURL Examples
```bash
# Create session
curl -X POST "http://localhost:8080/initiate-session" 
     -H "Content-Type: application/json" 
     -d '{"username": "sarah"}'

# Send message
curl -X POST "http://localhost:8080/query" 
     -H "Authorization: Bearer <SESSION_ID>" 
     -H "Content-Type: application/json" 
     -d '{"message": "Tell me about dinosaurs!"}'

# Add custom prompt
curl -X POST "http://localhost:8080/session/add-prompt" 
     -H "Authorization: Bearer <SESSION_ID>" 
     -H "Content-Type: application/json" 
     -d '{"additional_prompt": "Please act like a friendly math tutor"}'

# Test content filtering (will be blocked)
curl -X POST "http://localhost:8080/query" 
     -H "Authorization: Bearer <SESSION_ID>" 
     -H "Content-Type: application/json" 
     -d '{"message": "I hate math"}'
# Response: Kid-friendly redirection message
```

## AWS App Runner Deployment

This application is optimized for AWS App Runner deployment:

### Prerequisites
- AWS CLI configured
- Docker installed locally (for testing)
- OpenAI API key

### Deployment Steps
1. **Push to GitHub**: Ensure your code is in a GitHub repository
2. **Create App Runner Service**:
   - Go to AWS App Runner console
   - Create new service from GitHub repository
   - Select this repository
   - Use the included `apprunner.yaml` configuration
3. **Environment Variables**: Set in App Runner console:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `SECRET_KEY`: A secure random string

### AWS App Runner Features
- **Python 3.9 Compatible**: Optimized for AWS App Runner Python runtime
- **Auto Scaling**: Handles traffic spikes automatically
- **Health Checks**: Built-in health monitoring
- **HTTPS**: Automatic SSL certificate management
- **Container Support**: Uses optimized Docker container

### Local Testing with Docker
```bash
# Build the image
docker build -t kiddy-chat-api .

# Run locally (same as AWS App Runner)
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your_key \
  -e SECRET_KEY=your_secret \
  kiddy-chat-api
```

## Security Notes

1. **Session Management**: Sessions are stored in memory and expire after 24 hours
2. **API Key Security**: Keep your OpenAI API key secure and never commit it to version control
3. **TODO**: :
   - Using Redis or a database for session storage
   - Implementing rate limiting
   - Adding HTTPS/TLS encryption
   - Using proper secret management

## Contributing

Feel free to submit issues and pull requests to improve this chat application!

## License

MIT License
