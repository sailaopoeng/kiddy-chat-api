import os
import uuid
import re
import logging
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
import openai

app_version = "1.0.0"

# Configure logging for AWS App Runner
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs go to stdout for AWS App Runner
    ],
    force=True  # Override any existing logging configuration
)

# Ensure stdout is unbuffered for immediate log visibility in AWS App Runner
sys.stdout.reconfigure(line_buffering=True)

# Create logger for this module
logger = logging.getLogger(__name__)

# Set environment variable to ensure Python stdout is unbuffered
os.environ['PYTHONUNBUFFERED'] = '1'

# Load environment variables
load_dotenv()

def parse_openai_api_key(raw_key: str) -> Optional[str]:
    """
    Parse OpenAI API key from either text or JSON format
    AWS Secrets Manager can return either format depending on how it's configured
    
    Args:
        raw_key: The raw API key value from environment variable
        
    Returns:
        The extracted API key string, or None if parsing fails
    """
    if not raw_key:
        return None
        
    # Remove any leading/trailing whitespace
    raw_key = raw_key.strip()
    
    # Check if it's already a plain text API key
    if raw_key.startswith("sk-"):
        logger.info("API key detected as plain text format")
        return raw_key
    
    # Try to parse as JSON (AWS Secrets Manager format)
    try:
        key_data = json.loads(raw_key)
        logger.info("API key detected as JSON format")
        
        # Common JSON key names used in AWS Secrets Manager
        possible_keys = ['OPENAI_API_KEY', 'openai_api_key', 'api_key', 'key', 'apiKey']
        
        for key_name in possible_keys:
            if key_name in key_data:
                extracted_key = key_data[key_name]
                if extracted_key and isinstance(extracted_key, str) and extracted_key.startswith("sk-"):
                    logger.info(f"Successfully extracted API key from JSON field: {key_name}")
                    return extracted_key
        
        # If no standard key found, log available keys for debugging
        logger.warning(f"JSON format detected but no valid API key found. Available keys: {list(key_data.keys())}")
        return None
        
    except json.JSONDecodeError:
        # Not JSON format, might be some other format
        logger.warning("API key is not in plain text or valid JSON format")
        logger.warning(f"Raw key preview: {raw_key[:20]}..." if len(raw_key) > 20 else f"Raw key: {raw_key}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing API key: {e}")
        return None

# Initialize FastAPI app
app = FastAPI(
    title="Kiddy Chat API", 
    version=app_version,
    description="A safe and fun AI chat API designed specifically for kids!"
)

# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.on_event("startup")
async def startup_event():
    """Log application startup information"""
    logger.info("Kiddy Chat API is starting up!")
    logger.info("CORS middleware enabled - accepting requests from all origins")
    logger.info(f"OpenAI client status: {'Ready' if client else 'Failed'}")
    logger.info(f"API key status: {'Configured' if api_key else 'Missing'}")
    logger.info("Ready to serve safe and fun conversations for kids!")

@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown"""
    logger.info("Kiddy Chat API is shutting down. Goodbye!")

# Initialize OpenAI client with logging
raw_api_key = os.getenv("OPENAI_API_KEY")
logger.info("Checking OPENAI_API_KEY...")

if raw_api_key:
    logger.info(f"OPENAI_API_KEY environment variable found (length: {len(raw_api_key)} characters)")
    api_key = parse_openai_api_key(raw_api_key)
    
    if api_key:
        logger.info(f"Successfully parsed API key (length: {len(api_key)} characters)")
        logger.info(f"Key starts with: {api_key[:7]}..." if len(api_key) > 7 else "Key too short")
        if api_key.startswith("sk-"):
            logger.info("API key has correct format (starts with 'sk-')")
        else:
            logger.warning("Warning: API key doesn't start with 'sk-' - might be invalid")
    else:
        logger.error("Failed to parse API key from environment variable")
        api_key = None
else:
    logger.error("OPENAI_API_KEY not found in environment variables!")
    logger.info("Available environment variables:")
    for key in sorted(os.environ.keys()):
        if 'OPENAI' in key.upper() or 'API' in key.upper() or 'KEY' in key.upper():
            logger.info(f"   - {key}")
    api_key = None

try:
    client = openai.OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    client = None

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Security
security = HTTPBearer()

# In-memory session storage (in production, use Redis or database)
sessions: Dict[str, Dict] = {}

# Pydantic models
class InitiateSessionRequest(BaseModel):
    username: str

class InitiateSessionResponse(BaseModel):
    session_id: str
    message: str
    username: str

class QueryRequest(BaseModel):
    message: str

class QueryResponse(BaseModel):
    response: str
    session_id: str
    username: str

class ChatMessage(BaseModel):
    role: str
    content: str

class AddPromptRequest(BaseModel):
    additional_prompt: str

class AddPromptResponse(BaseModel):
    message: str
    session_id: str
    additional_prompt: str

class FilterInfoResponse(BaseModel):
    inappropriate_words: List[str]
    inappropriate_patterns: List[str]
    kids_friendly_responses: List[str]
    default_system_prompt: str

# Kid-friendly content filtering
INAPPROPRIATE_WORDS = [
    # Add common inappropriate words that kids shouldn't use
    "stupid", "idiot", "hate", "kill", "die", "death", "blood", "violence", "weapon",
    "gun", "knife", "fight", "hurt", "pain", "scary", "monster", "devil", "hell",
    "damn", "crap", "shut up", "loser", "dumb", "ugly", "fat", "skinny"
]

# Additional patterns to check
INAPPROPRIATE_PATTERNS = [
    r'\b(i hate|you suck|go away|shut up)\b',
    r'\b(stupid|dumb|idiot)\s+(person|kid|child|boy|girl)\b',
    r'\b(kill|hurt|hit|punch|kick)\s+(someone|somebody|people)\b'
]

KIDS_FRIENDLY_RESPONSES = [
    "I can't help with that kind of talk. Let's use kind words instead! 😊",
    "Oops! That's not very nice language. How about we talk about something fun instead?",
    "Let's keep our conversation friendly and positive! What would you like to learn about today?",
    "I'm here to have nice conversations with you. Can we use gentler words please?",
    "That doesn't sound very kind. Let's chat about something that makes you happy! 🌟"
]

def contains_inappropriate_content(message: str) -> bool:
    """Check if message contains inappropriate content for kids"""
    message_lower = message.lower().strip()
    
    # Check for inappropriate words
    for word in INAPPROPRIATE_WORDS:
        # Use word boundaries to ensure whole word matching
        if re.search(rf'\b{re.escape(word)}\b', message_lower):
            return True
    
    # Check for inappropriate patterns
    for pattern in INAPPROPRIATE_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return True
    
    return False

def get_kid_friendly_response() -> str:
    """Get a random kid-friendly response for inappropriate content"""
    import random
    return random.choice(KIDS_FRIENDLY_RESPONSES)

def get_kids_system_prompt() -> str:
    """Get the system prompt for kid-friendly AI assistant"""
    return """You are a helpful, friendly, and safe AI assistant designed specifically for children. Please follow these guidelines:

1. ALWAYS use simple, age-appropriate language that kids can understand
2. Be encouraging, positive, and supportive in all responses
3. Focus on education, creativity, fun facts, stories, games, and learning
4. NEVER discuss topics that might be scary, violent, inappropriate, or harmful
5. If asked about adult topics, gently redirect to kid-friendly alternatives
6. Encourage curiosity, learning, and positive behavior
7. Use emojis occasionally to make conversations fun 😊
8. Be patient and explain things in simple terms
9. Promote kindness, respect, and good values
10. If you're unsure about a topic's appropriateness, choose not to discuss it

Remember: You're talking to a child, so keep everything safe, educational, and fun!"""

# Session management
def create_session(username: str, additional_prompt: str = None) -> str:
    """Create a new session for a user with optional additional prompt"""
    session_id = str(uuid.uuid4())
    
    # Build system prompt
    base_prompt = get_kids_system_prompt()
    if additional_prompt:
        combined_prompt = f"{base_prompt}\n\nAdditional instructions for this session: {additional_prompt}"
        logger.info(f"Creating session {session_id[:8]}... for {username} with additional prompt")
    else:
        combined_prompt = base_prompt
        logger.info(f"Creating session {session_id[:8]}... for {username} with default prompt")
    
    sessions[session_id] = {
        "username": username,
        "created_at": datetime.now(),
        "last_activity": datetime.now(),
        "additional_prompt": additional_prompt,
        "messages": [
            {
                "role": "system",
                "content": combined_prompt
            }
        ]
    }
    
    logger.info(f"Session {session_id[:8]}... created successfully. Total active sessions: {len(sessions)}")
    return session_id

def validate_session(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Validate session token"""
    session_id = credentials.credentials
    
    if session_id not in sessions:
        logger.warning(f"Invalid session ID attempted: {session_id[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session ID"
        )
    
    # Update last activity
    sessions[session_id]["last_activity"] = datetime.now()
    logger.debug(f"Session validated and activity updated: {session_id[:8]}...")
    
    return session_id

def cleanup_expired_sessions():
    """Clean up sessions older than 24 hours"""
    cutoff_time = datetime.now() - timedelta(hours=24)
    expired_sessions = [
        session_id for session_id, session_data in sessions.items()
        if session_data["last_activity"] < cutoff_time
    ]
    
    if expired_sessions:
        logger.info(f"Cleaning up {len(expired_sessions)} expired sessions")
        for session_id in expired_sessions:
            del sessions[session_id]
    
    logger.debug(f"Session cleanup complete. Active sessions: {len(sessions)}")

# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint with kid-friendly message"""
    return {
        "message": "Welcome to Kiddy Chat API! 🌟 A safe and fun place to chat with AI! 🤖",
        "status": "Ready for awesome conversations!",
        "version": app_version,
        "openai_api_key_status": "configured" if api_key else "missing",
        "openai_client_status": "initialized" if client else "failed"
    }

@app.post("/initiate-session", response_model=InitiateSessionResponse)
async def initiate_session(request: InitiateSessionRequest):
    """
    Create a new chat session for a user
    """
    logger.info(f"Creating new session for username: {request.username}")
    
    if not request.username.strip():
        logger.warning(f"Empty username provided in session creation request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username cannot be empty"
        )
    
    # Clean up expired sessions
    cleanup_expired_sessions()
    
    # Create new session
    session_id = create_session(request.username)
    
    logger.info(f"Session {session_id} created successfully for user: {request.username}")
    
    return InitiateSessionResponse(
        session_id=session_id,
        message=f"Session created successfully for {request.username}",
        username=request.username
    )

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, session_id: str = Depends(validate_session)):
    """
    Send a message to GPT and get a kid-friendly response
    Requires valid session ID in Authorization header as Bearer token
    """
    if not request.message.strip():
        logger.warning(f"Empty message provided in query request for session: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty"
        )
    
    session_data = sessions[session_id]
    username = session_data["username"]
    
    logger.info(f"Processing query for user {username} (session: {session_id[:8]}...): {request.message[:50]}...")
    
    # Check for inappropriate content
    if contains_inappropriate_content(request.message):
        logger.warning(f"Inappropriate content detected from user {username}: {request.message[:30]}...")
        kid_friendly_response = get_kid_friendly_response()
        
        # Still add the user message to history for context, but don't send to OpenAI
        session_data["messages"].append({
            "role": "user",
            "content": request.message
        })
        
        # Add the kid-friendly response
        session_data["messages"].append({
            "role": "assistant",
            "content": kid_friendly_response
        })
        
        return QueryResponse(
            response=kid_friendly_response,
            session_id=session_id,
            username=username
        )
    
    # Add user message to session history
    session_data["messages"].append({
        "role": "user",
        "content": request.message
    })
    
    try:
        logger.info(f"Sending request to OpenAI for user {username}")
        # Create OpenAI chat completion with kid-friendly model
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=session_data["messages"],
            max_tokens=300,  # Reduced for kid-appropriate responses
            temperature=0.5,  # Lower temperature for more consistent, safer responses
            frequency_penalty=0.3,
            presence_penalty=0.3
        )
        
        # Extract assistant response
        assistant_message = response.choices[0].message.content
        logger.info(f"Received response from OpenAI for user {username}: {assistant_message[:50]}...")
        
        # Additional safety check on AI response
        if contains_inappropriate_content(assistant_message):
            logger.warning(f"Inappropriate content detected in AI response for user {username}")
            assistant_message = "I want to make sure I'm being helpful and appropriate. Let me think of a better way to answer that! What else would you like to know? 😊"
        
        # Add assistant response to session history
        session_data["messages"].append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return QueryResponse(
            response=assistant_message,
            session_id=session_id,
            username=username
        )
        
    except Exception as e:
        logger.error(f"Error processing OpenAI request for user {username}: {str(e)}")
        # Kid-friendly error message
        error_response = "Oops! I'm having a little trouble right now. Can you try asking me something else? 🤖"
        
        session_data["messages"].append({
            "role": "assistant",
            "content": error_response
        })
        
        return QueryResponse(
            response=error_response,
            session_id=session_id,
            username=username
        )

@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str = Depends(validate_session)):
    """
    Get chat history for a session
    """
    session_data = sessions[session_id]
    
    return {
        "session_id": session_id,
        "username": session_data["username"],
        "created_at": session_data["created_at"],
        "messages": session_data["messages"]
    }

@app.delete("/session")
async def end_session(session_id: str = Depends(validate_session)):
    """
    End a chat session
    """
    username = sessions[session_id]["username"]
    del sessions[session_id]
    
    logger.info(f"Session ended for user {username}. Session ID: {session_id[:8]}... Active sessions: {len(sessions)}")
    
    return {
        "message": f"Session ended successfully for {username}",
        "session_id": session_id
    }

@app.get("/sessions/active")
async def get_active_sessions():
    """
    Get count of active sessions (for monitoring)
    """
    cleanup_expired_sessions()
    return {
        "active_sessions": len(sessions)    
    }
    # "session_ids": list(sessions.keys())

@app.get("/conversation-starters")
async def get_conversation_starters():
    """
    Get fun conversation starters for kids
    """
    import random
    
    starters = [
        "What's your favorite animal and why? 🐾",
        "If you could have any superpower, what would it be? 🦸‍♂️",
        "What's the coolest thing you learned today? 📚",
        "If you could visit any planet, which one would you choose? 🚀",
        "What's your favorite color and what does it remind you of? 🌈",
        "If you could be friends with any cartoon character, who would it be? 📺",
        "What's your favorite season and what do you like to do in it? ⛄🌸☀️🍂",
        "If you could invent something amazing, what would it be? 💡",
        "What's the funniest joke you know? 😄",
        "If you could fly like a bird, where would you go first? 🐦",
        "What's your favorite book or story? 📖",
        "If you could talk to animals, what would you ask them? 🗣️🐕",
        "What makes you really happy? 😊",
        "If you could build the coolest treehouse, what would be in it? 🏠🌳",
        "What's the most interesting place you've ever been? 🗺️"
    ]
    
    # Return 5 random starters
    selected_starters = random.sample(starters, min(5, len(starters)))
    
    return {
        "conversation_starters": selected_starters,
        "message": "Here are some fun things we can chat about! 🌟"
    }

@app.get("/debug/env-check")
async def debug_environment():
    """
    Debug endpoint to check environment variable status
    """
    raw_api_key = os.getenv("OPENAI_API_KEY")
    parsed_api_key = parse_openai_api_key(raw_api_key) if raw_api_key else None
    
    env_info = {
        "openai_api_key_raw_present": bool(raw_api_key),
        "openai_api_key_raw_length": len(raw_api_key) if raw_api_key else 0,
        "openai_api_key_parsed_present": bool(parsed_api_key),
        "openai_api_key_parsed_length": len(parsed_api_key) if parsed_api_key else 0,
        "openai_api_key_format_valid": parsed_api_key.startswith("sk-") if parsed_api_key else False,
        "openai_client_initialized": client is not None,
        "port": os.getenv("PORT", "not_set"),
        "python_path": os.getenv("PYTHONPATH", "not_set"),
        "environment_variables_with_key_or_api": [
            key for key in os.environ.keys() 
            if any(word in key.upper() for word in ['OPENAI', 'API', 'KEY'])
        ]
    }
    
    # Add format detection
    if raw_api_key:
        raw_preview = f"{raw_api_key[:20]}..." if len(raw_api_key) > 20 else raw_api_key
        env_info["openai_api_key_raw_preview"] = raw_preview
        
        # Detect format
        if raw_api_key.strip().startswith("sk-"):
            env_info["detected_format"] = "plain_text"
        elif raw_api_key.strip().startswith("{"):
            env_info["detected_format"] = "json"
        else:
            env_info["detected_format"] = "unknown"
    
    if parsed_api_key:
        env_info["openai_api_key_parsed_preview"] = f"{parsed_api_key[:7]}..." if len(parsed_api_key) > 7 else "too_short"
    
    return env_info

@app.get("/filter-info", response_model=FilterInfoResponse)
async def get_filter_info():
    """
    Get current filter words, patterns, and system prompts for frontend display
    """
    return FilterInfoResponse(
        inappropriate_words=INAPPROPRIATE_WORDS,
        inappropriate_patterns=INAPPROPRIATE_PATTERNS,
        kids_friendly_responses=KIDS_FRIENDLY_RESPONSES,
        default_system_prompt=get_kids_system_prompt()
    )

@app.post("/session/add-prompt", response_model=AddPromptResponse)
async def add_session_prompt(request: AddPromptRequest, session_id: str = Depends(validate_session)):
    """
    Add an additional prompt to the current session (appends to default prompt)
    This allows frontend to customize behavior without overwriting safety defaults
    """
    if not request.additional_prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Additional prompt cannot be empty"
        )
    
    session_data = sessions[session_id]
    
    # Update the additional prompt for this session
    session_data["additional_prompt"] = request.additional_prompt
    
    # Rebuild the system prompt with the additional instruction
    base_prompt = get_kids_system_prompt()
    combined_prompt = f"{base_prompt}\n\nAdditional instructions for this session: {request.additional_prompt}"
    
    # Update the system message in the conversation history
    if session_data["messages"] and session_data["messages"][0]["role"] == "system":
        session_data["messages"][0]["content"] = combined_prompt
    else:
        # If no system message exists, add one at the beginning
        session_data["messages"].insert(0, {
            "role": "system",
            "content": combined_prompt
        })
    
    return AddPromptResponse(
        message="Additional prompt added successfully! This will guide our conversation while keeping all safety features active.",
        session_id=session_id,
        additional_prompt=request.additional_prompt
    )

@app.get("/session/prompt-info")
async def get_session_prompt_info(session_id: str = Depends(validate_session)):
    """
    Get the current session's prompt information including any additional prompts
    """
    session_data = sessions[session_id]
    
    return {
        "session_id": session_id,
        "username": session_data["username"],
        "default_system_prompt": get_kids_system_prompt(),
        "additional_prompt": session_data.get("additional_prompt"),
        "combined_system_message": session_data["messages"][0]["content"] if session_data["messages"] and session_data["messages"][0]["role"] == "system" else None,
        "created_at": session_data["created_at"]
    }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting Kiddy Chat API ({app_version}) on port {port} [{'Production' if os.getenv('PORT') else 'Development'}]")
    uvicorn.run(app, host="0.0.0.0", port=port)
