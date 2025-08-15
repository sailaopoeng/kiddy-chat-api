# Kiddy Chat API 🌟

A safe and fun FastAPI-based chat application designed specifically for kids! This app integrates with OpenAI's GPT-4o-mini model and includes comprehensive content filtering to ensure age-appropriate conversations.

## ✨ Features

### 🛡️ Kid-Safety Features
- **Content Filtering**: Automatically detects and blocks inappropriate language
- **Age-Appropriate Responses**: System prompts ensure kid-friendly interactions  
- **Safe AI Model**: Uses GPT-4o-mini with reduced temperature for consistent, safe responses
- **Dual-Layer Protection**: Input and output filtering for maximum safety

### 🎨 Interactive Features
- **Fun Interface**: Emojis and encouraging language throughout
- **Conversation Starters**: Built-in suggestions for fun topics
- **Educational Focus**: Encourages learning, creativity, and positive values
- **Custom Session Prompts**: Frontend can add educational context while maintaining safety

### 🚀 Core API Features
- **Session Management**: Create and manage chat sessions with unique session IDs
- **Authentication**: Bearer token authentication using session IDs
- **Chat History**: Maintain conversation context within sessions
- **RESTful API**: Clean and well-documented endpoints
- **Filter Transparency**: API endpoints to view current filters and prompts

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

Visit `http://localhost:8000/docs` for interactive API documentation.

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
    "inappropriate_words": ["stupid", "idiot", "hate", "kill", "..."],
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
curl -X POST "http://localhost:8000/initiate-session" 
     -H "Content-Type: application/json" 
     -d '{"username": "sarah"}'

# Send message
curl -X POST "http://localhost:8000/query" 
     -H "Authorization: Bearer <SESSION_ID>" 
     -H "Content-Type: application/json" 
     -d '{"message": "Tell me about dinosaurs!"}'

# Add custom prompt
curl -X POST "http://localhost:8000/session/add-prompt" 
     -H "Authorization: Bearer <SESSION_ID>" 
     -H "Content-Type: application/json" 
     -d '{"additional_prompt": "Please act like a friendly math tutor"}'

# Test content filtering (will be blocked)
curl -X POST "http://localhost:8000/query" 
     -H "Authorization: Bearer <SESSION_ID>" 
     -H "Content-Type: application/json" 
     -d '{"message": "I hate math"}'
# Response: Kid-friendly redirection message
```

## 🛡️ Safety System

### Content Filtering
The API automatically filters:
- ❌ Inappropriate language and words
- ❌ Violent or scary content  
- ❌ Adult topics
- ❌ Negative or harmful speech patterns

### Safety Response Strategy
When inappropriate content is detected:
1. 🚫 Block content from reaching OpenAI
2. 💬 Respond with gentle, educational message
3. 🔄 Redirect to positive conversation topics
4. 📝 Log interaction for monitoring (if needed)

### AI Configuration
- **Model**: GPT-4o-mini (OpenAI's latest efficient model)
- **Temperature**: 0.5 (consistent, predictable responses)
- **Max Tokens**: 300 (appropriate response length for kids)
- **Content Moderation**: Dual-layer filtering (input + output)

### Custom Session Prompts
- ✅ **Additive Only**: Appended to default safety prompt, never replacing it
- ✅ **Session Scoped**: Each session can have different additional instructions
- ✅ **Safety Preserved**: All content filtering remains active
- ✅ **Educational Use**: Perfect for math tutoring, science teaching, creative writing

## 📁 Project Structure

```
gpt-for-kids-backend/
├── main.py              # Main FastAPI application
├── requirements.txt     # Python dependencies  
├── .env                # Environment variables (create this)
├── Dockerfile          # Docker container configuration
└── README.md           # This documentation
```

## 🔧 Error Handling

- **400 Bad Request**: Invalid input (empty username/message)
- **401 Unauthorized**: Invalid or missing session ID  
- **500 Internal Server Error**: OpenAI API errors

## 🔒 Security Notes

- **Session Management**: Sessions stored in memory, expire after 24 hours
- **API Key Security**: Keep OpenAI API key secure, never commit to version control
- **Production TODO**: Redis/database storage, rate limiting, HTTPS/TLS, secret management

## 📄 License

MIT License

### Using cURL

```bash
# Get filter and prompt information
curl -X GET "http://localhost:8000/filter-info"

# Create a session
curl -X POST "http://localhost:8000/initiate-session" \
     -H "Content-Type: application/json" \
     -d '{"username": "sarah"}'

# Add custom session prompt
curl -X POST "http://localhost:8000/session/add-prompt" \
     -H "Authorization: Bearer <SESSION_ID>" \
     -H "Content-Type: application/json" \
     -d '{"additional_prompt": "Please act like a friendly math tutor who uses fun examples"}'

# Get session prompt info
curl -X GET "http://localhost:8000/session/prompt-info" \
     -H "Authorization: Bearer <SESSION_ID>"

# Send a message with custom prompt active
curl -X POST "http://localhost:8000/query" \
     -H "Authorization: Bearer <SESSION_ID>" \
     -H "Content-Type: application/json" \
     -d '{"message": "How do fractions work?"}'

# Test that filtering still works
curl -X POST "http://localhost:8000/query" \
     -H "Authorization: Bearer <SESSION_ID>" \
     -H "Content-Type: application/json" \
     -d '{"message": "I hate math"}'
# Response: Kid-friendly redirection message
```s inappropriate language
- **👶 Age-Appropriate Responses**: System prompts ensure kid-friendly interactions
- **🎨 Fun Interface**: Emojis and encouraging language throughout
- **🎯 Conversation Starters**: Built-in suggestions for fun topics
- **🤖 Safe AI Model**: Uses GPT-4o-mini with reduced temperature for consistent, safe responses
- **📚 Educational Focus**: Encourages learning, creativity, and positive values

## 🚀 Core Features

- **Session Management**: Create and manage chat sessions with unique session IDs
- **Authentication**: Bearer token authentication using session IDs
- **OpenAI Integration**: Powered by GPT-4o-mini for intelligent, kid-safe responses
- **Chat History**: Maintain conversation context within sessions
- **RESTful API**: Clean and well-documented API endpoints

## Setup

### 1. Environment Setup

Make sure you have Python 3.8+ installed, then install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root and add your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_secret_key_here
```

**Important**: Replace `your_openai_api_key_here` with your actual OpenAI API key from https://platform.openai.com/api-keys

### 3. Running the Application

Start the FastAPI server:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`

### 4. API Documentation

Once running, visit these URLs for interactive API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📚 API Endpoints

### 1. Welcome Message
**GET** `/`

Get a kid-friendly welcome message and API status.

**Response:**
```json
{
    "message": "Welcome to Kiddy Chat API! 🌟 A safe and fun place to chat with AI! 🤖",
    "status": "Ready for awesome conversations!",
    "version": "1.0.0"
}
```

### 2. Initiate Session
**POST** `/initiate-session`

Create a new chat session for a young user.

**Request Body:**
```json
{
    "username": "emma"
}
```

**Response:**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Session created successfully for emma",
    "username": "emma"
}
```

### 3. Query (Kid-Safe Chat)
**POST** `/query`

Send a message and get a kid-friendly response with content filtering.

**Headers:**
```
Authorization: Bearer <session_id>
```

**Request Body:**
```json
{
    "message": "What's your favorite animal?"
}
```

**Response:**
```json
{
    "response": "I love learning about all animals! 🐾 Dolphins are really cool because they're super smart and friendly. They can recognize themselves in mirrors and love to play! What about you - do you have a favorite animal? I'd love to hear about it! 😊",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "emma"
}
```

**Content Filtering Example:**
If inappropriate content is detected, you'll get a gentle response like:
```json
{
    "response": "I can't help with that kind of talk. Let's use kind words instead! 😊",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "emma"
}
```

### 4. Conversation Starters
**GET** `/conversation-starters`

Get fun, kid-appropriate conversation topics.

**Response:**
```json
{
    "conversation_starters": [
        "What's your favorite animal and why? 🐾",
        "If you could have any superpower, what would it be? 🦸‍♂️",
        "What's the coolest thing you learned today? 📚",
        "If you could visit any planet, which one would you choose? 🚀",
        "What's your favorite color and what does it remind you of? 🌈"
    ],
    "message": "Here are some fun things we can chat about! 🌟"
}
```

### 5. Get Session History
### 5. Get Session History
**GET** `/session/{session_id}/history`

Retrieve chat history for a session.

**Headers:**
```
Authorization: Bearer <session_id>
```

**Response:**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "emma",
    "created_at": "2024-01-15T10:30:00",
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful, friendly, and safe AI assistant designed specifically for children..."
        },
        {
            "role": "user",
            "content": "What's your favorite animal?"
        },
        {
            "role": "assistant",
            "content": "I love learning about all animals! 🐾 Dolphins are really cool..."
        }
    ]
}
```

### 6. End Session
**DELETE** `/session`

End a chat session and clean up resources.

**Headers:**
```
Authorization: Bearer <session_id>
```

**Response:**
```json
{
    "message": "Session ended successfully for emma",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 7. Get Filter & Prompt Information
**GET** `/filter-info`

Retrieve current content filters, patterns, and system prompts for frontend display.

**Response:**
```json
{
    "inappropriate_words": ["stupid", "idiot", "hate", "kill", "..."],
    "inappropriate_patterns": ["\\b(i hate|you suck|go away|shut up)\\b", "..."],
    "kids_friendly_responses": [
        "I can't help with that kind of talk. Let's use kind words instead! 😊",
        "Oops! That's not very nice language. How about we talk about something fun instead?",
        "..."
    ],
    "default_system_prompt": "You are a helpful, friendly, and safe AI assistant designed specifically for children..."
}
```

### 8. Add Custom Session Prompt
**POST** `/session/add-prompt`

Add additional instructions to the current session (appends to default prompt without overriding safety features).

**Headers:**
```
Authorization: Bearer <session_id>
```

**Request Body:**
```json
{
    "additional_prompt": "Please respond like a friendly science teacher who loves to explain things with simple experiments."
}
```

**Response:**
```json
{
    "message": "Additional prompt added successfully! This will guide our conversation while keeping all safety features active.",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "additional_prompt": "Please respond like a friendly science teacher who loves to explain things with simple experiments."
}
```

### 9. Get Session Prompt Information
**GET** `/session/prompt-info`

Get detailed information about the current session's prompts and configuration.

**Headers:**
```
Authorization: Bearer <session_id>
```

**Response:**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "emma",
    "default_system_prompt": "You are a helpful, friendly, and safe AI assistant...",
    "additional_prompt": "Please respond like a friendly science teacher...",
    "combined_system_message": "You are a helpful, friendly, and safe AI assistant designed specifically for children...\n\nAdditional instructions for this session: Please respond like a friendly science teacher...",
    "created_at": "2024-01-15T10:30:00"
}
```

## 🛡️ Content Safety Features

### Inappropriate Content Filtering

The API automatically filters out:
- ❌ Inappropriate language and words
- ❌ Violent or scary content  
- ❌ Adult topics
- ❌ Negative or harmful speech patterns

### Kid-Friendly System Prompts

Every conversation starts with a comprehensive system prompt that ensures the AI:
- ✅ Uses simple, age-appropriate language
- ✅ Stays positive and encouraging
- ✅ Focuses on education and creativity
- ✅ Promotes kindness and good values
- ✅ Redirects inappropriate topics to fun alternatives

### Safe AI Configuration

- **Model**: GPT-4o-mini (OpenAI's efficient model)
- **Temperature**: 0.5 (lower for more consistent, predictable responses)
- **Max Tokens**: 300 (appropriate response length for kids)
- **Content Moderation**: Dual-layer filtering (input + output)

## 🎯 Authentication

The API uses Bearer token authentication:

1. **Create a session** using `/initiate-session` with a username
2. **Use the returned session_id** as a Bearer token in subsequent requests
3. **Include the token** in the Authorization header: `Authorization: Bearer <session_id>`

**Without a valid session ID, the `/query` endpoint will return 401 Unauthorized.**


### Using cURL

```bash
# 1. Create a session
curl -X POST "http://localhost:8000/initiate-session" \
     -H "Content-Type: application/json" \
     -d '{"username": "sarah"}'

# Response: {"session_id": "abc123...", ...}

# 2. Send a kid-friendly message (replace <SESSION_ID> with actual session ID)
curl -X POST "http://localhost:8000/query" \
     -H "Authorization: Bearer <SESSION_ID>" \
     -H "Content-Type: application/json" \
     -d '{"message": "Tell me about dinosaurs!"}'

# 3. Try inappropriate content (will be filtered)
curl -X POST "http://localhost:8000/query" \
     -H "Authorization: Bearer <SESSION_ID>" \
     -H "Content-Type: application/json" \
     -d '{"message": "I hate school"}'
# Response: Kid-friendly redirection message

# 4. Get chat history
curl -X GET "http://localhost:8000/session/<SESSION_ID>/history" \
     -H "Authorization: Bearer <SESSION_ID>"

# 5. End session
curl -X DELETE "http://localhost:8000/session" \
     -H "Authorization: Bearer <SESSION_ID>"
```

## 📁 Project Structure

```
gpt-for-kids-backend/
├── main.py                 # Main FastAPI application with kid-safety features
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables (create this)
├── Dockerfile             # Docker container configuration
└── README.md              # This documentation
```

## 🔧 Advanced Features

### Custom Session Prompts

**Purpose**: Allow frontend applications to customize AI behavior for specific educational contexts while maintaining all safety features.

**Key Features**:
- ✅ **Additive Only**: Custom prompts are appended to the default safety prompt, never replacing it
- ✅ **Session Scoped**: Each session can have its own additional instructions
- ✅ **Safety Preserved**: All content filtering and kid-safety features remain active
- ✅ **Frontend Integration**: Easy API endpoints for dynamic prompt management

**Example Use Cases**:
- 📚 "Act like a friendly math tutor"
- 🔬 "Focus on science experiments and fun facts"
- 🎨 "Help with creative writing and storytelling"
- 🌍 "Discuss geography and different cultures"

### Filter Information API

**Purpose**: Provide transparency to frontend developers about what content is filtered and how the system works.

**Available Information**:
- 🚫 **Filtered Words**: List of inappropriate words that are blocked
- 🔍 **Filter Patterns**: Regex patterns used to detect problematic content
- 💬 **Alternative Responses**: Kid-friendly responses used when content is filtered
- 📝 **System Prompts**: The base safety prompt used for all sessions

**Frontend Integration Benefits**:
- Help developers understand the safety system
- Enable dynamic UI updates based on current filters
- Assist in creating complementary frontend validation
- Support educational content about appropriate language

## 🔧 Content Filtering Details

### Blocked Words and Patterns
The system monitors for:
- Basic inappropriate words
- Negative speech patterns  
- Violence-related content
- Adult topics
- Bullying language

### Response Strategy
When inappropriate content is detected:
1. 🚫 Block the content from reaching OpenAI
2. 💬 Respond with a gentle, educational message
3. 🔄 Redirect to positive conversation topics
4. 📝 Still log the interaction for monitoring (if needed)

### Customizable Filtering
You can easily modify the content filters in `main.py`:
- `INAPPROPRIATE_WORDS` list
- `INAPPROPRIATE_PATTERNS` regex patterns  
- `KIDS_FRIENDLY_RESPONSES` alternative responses

## Error Handling

The API includes comprehensive error handling:

- **400 Bad Request**: Invalid input (empty username/message)
- **401 Unauthorized**: Invalid or missing session ID
- **500 Internal Server Error**: OpenAI API errors or server issues

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
