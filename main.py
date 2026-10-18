import asyncio
import hashlib
import hmac
import os
import time
import uuid
import re
import logging
import sys
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List

from fastapi import FastAPI, HTTPException, Depends, Header, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import openai

try:
    from upstash_redis.asyncio import Redis as AsyncRedis
except ImportError:
    AsyncRedis = None

app_version = "1.0.0"

# Configure logging for AWS App Runner and Vercel functions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs go to stdout for hosted runtimes
    ],
    force=True  # Override any existing logging configuration
)

# Ensure stdout is unbuffered for immediate log visibility in hosted runtimes
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

# Create logger for this module
logger = logging.getLogger(__name__)

# Set environment variable to ensure Python stdout is unbuffered
os.environ['PYTHONUNBUFFERED'] = '1'

# Load environment variables
load_dotenv()

SESSION_TTL_SECONDS = 24 * 60 * 60
SESSION_INDEX_KEY = "sessions:index"
SESSION_KEY_PREFIX = "session:"

OPENAI_MODEL = "gpt-5.6-luna"
# GPT-5.x models reject max_tokens/temperature/penalties.
# Budget includes hidden reasoning tokens, so keep it generous;
# reply length is kept short by the system prompt.
MAX_COMPLETION_TOKENS = 1000

# Input size limits (longer requests get HTTP 422)
MAX_USERNAME_LENGTH = 50
MAX_MESSAGE_LENGTH = 2000
MAX_ADDITIONAL_PROMPT_LENGTH = 2000

# Messages allowed per session per minute. 0 turns the limit off.
QUERY_RATE_LIMIT_PER_MINUTE = int(os.getenv("QUERY_RATE_LIMIT_PER_MINUTE", "20"))

# Grown-up PIN (optional). When PARENT_PIN is set, changing a session's
# instructions needs either a short-lived parent token (from /parent/verify)
# or instructions that were approved with the PIN before (their signature).
PARENT_TOKEN_TTL_SECONDS = 15 * 60
PIN_MAX_FAILURES_PER_CLIENT = 5
PIN_MAX_FAILURES_TOTAL = 30
PIN_LOCKOUT_SECONDS = 15 * 60

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
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing API key: {e}")
        return None

# Initialize FastAPI app
app = FastAPI(
    title="Kiddy Chat API", 
    version=app_version,
    description="A safe and fun AI chat API designed specifically for kids!",
    redoc_url=None
)

def get_allowed_origins() -> List[str]:
    """Read comma-separated allowed origins from the environment."""
    raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["*"]

allowed_origins = get_allowed_origins()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials="*" not in allowed_origins,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Like FastAPI's default 422 response, but without echoing the rejected input.
    Input with broken characters (such as half an emoji) can't be encoded as
    UTF-8, so echoing it crashed the request with a 500 that had no CORS
    headers, which browsers report as a network error.
    """
    errors = [
        {"type": error.get("type"), "loc": list(error.get("loc", ())), "msg": error.get("msg")}
        for error in exc.errors()
    ]
    return Response(
        content=json.dumps({"detail": errors}, ensure_ascii=True, default=str),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        media_type="application/json",
    )

@app.on_event("startup")
async def startup_event():
    """Log application startup information"""
    logger.info("Kiddy Chat API is starting up!")
    logger.info(f"CORS middleware enabled for origins: {allowed_origins}")
    logger.info(f"OpenAI client status: {'Ready' if client else 'Failed'}")
    logger.info(f"API key status: {'Configured' if api_key else 'Missing'}")
    logger.info(f"Session storage: {await current_store_mode()}")
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
    logger.warning("OPENAI_API_KEY not found in environment variables")
    logger.info("Available environment variables:")
    for key in sorted(os.environ.keys()):
        if 'OPENAI' in key.upper() or 'API' in key.upper() or 'KEY' in key.upper():
            logger.info(f"   - {key}")
    api_key = None

try:
    # Async client so a slow OpenAI call doesn't block other requests.
    client = openai.AsyncOpenAI(api_key=api_key)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    client = None

# Grown-up PIN setup
parent_pin: Optional[str] = (os.getenv("PARENT_PIN") or "").strip() or None

def build_parent_signing_key() -> Optional[bytes]:
    """
    Key for signing parent tokens and approved instructions.
    Uses PARENT_SIGNING_SECRET when set; otherwise it is derived from the PIN and
    the OpenAI key, so it is stable across instances without extra setup.
    Changing either one makes earlier approvals invalid.
    """
    if not parent_pin:
        return None
    secret = os.getenv("PARENT_SIGNING_SECRET")
    if secret:
        return secret.encode()
    if not api_key:
        logger.warning("PARENT_PIN is set without PARENT_SIGNING_SECRET or OPENAI_API_KEY; set PARENT_SIGNING_SECRET")
    return hashlib.sha256(f"kiddy-parent-v1|{parent_pin}|{api_key or ''}".encode()).digest()

parent_signing_key = build_parent_signing_key()
if parent_pin:
    logger.info("Grown-up PIN is enabled for changing session instructions")
    if len(parent_pin) < 6:
        logger.warning("PARENT_PIN is shorter than 6 characters; a longer PIN is harder to guess")
else:
    logger.info("PARENT_PIN not set; anyone with a session can change its instructions")

# Security
security = HTTPBearer()

# In-process session store. Used when Redis is not configured, and as a fallback
# whenever Redis calls fail. Sessions here are lost on cold starts and are not
# shared between instances.
sessions: Dict[str, Dict] = {}

# Checked in order; the first pair with both URL and token set wins.
REDIS_ENV_PAIRS = [
    ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"),
    ("UPSTASH2_KV_REST_API_URL", "UPSTASH2_KV_REST_API_TOKEN"),
    ("KV_REST_API_URL", "KV_REST_API_TOKEN"),
]

# Upper bound for a single Redis call. The upstash client has no HTTP timeout
# of its own, so without this a hung connection could stall a request.
REDIS_OP_TIMEOUT_SECONDS = 3.0
# After a Redis failure, skip Redis for this long so requests don't keep
# waiting on a dead database.
REDIS_FAILURE_COOLDOWN_SECONDS = 60
KEEPALIVE_KEY = "keepalive"
KEEPALIVE_TTL_SECONDS = 24 * 60 * 60

def resolve_redis_config() -> Optional[Dict[str, str]]:
    for url_var, token_var in REDIS_ENV_PAIRS:
        url = os.getenv(url_var)
        token = os.getenv(token_var)
        if url and token:
            return {"url": url, "token": token, "source": url_var}
    return None

redis_config = resolve_redis_config()
redis_client = None
if AsyncRedis and redis_config:
    try:
        redis_client = AsyncRedis(
            url=redis_config["url"],
            token=redis_config["token"],
            allow_telemetry=False,
            # Fail fast; the in-memory fallback handles errors instead of a 3s retry.
            rest_retries=0,
        )
        logger.info(f"Redis configured from {redis_config['source']}")
    except Exception as e:
        logger.warning(f"Could not create Redis client ({type(e).__name__}); using in-memory sessions")
        redis_client = None
elif not redis_config:
    logger.info("No Redis env vars found; using in-memory sessions")

# None = not checked yet on this instance, True = last call worked, False = last call failed.
redis_healthy: Optional[bool] = None
redis_last_failure_at = 0.0

def mark_redis_failure(operation: str, error: Exception):
    global redis_healthy, redis_last_failure_at
    redis_healthy = False
    redis_last_failure_at = time.monotonic()
    logger.warning(
        f"Redis {operation} failed ({type(error).__name__}); "
        f"using in-memory sessions for the next {REDIS_FAILURE_COOLDOWN_SECONDS}s"
    )

def mark_redis_success():
    global redis_healthy
    if redis_healthy is False:
        logger.info("Redis is reachable again; switching back to Redis sessions")
    redis_healthy = True

async def redis_call(awaitable):
    """Run one Redis command with a timeout."""
    return await asyncio.wait_for(awaitable, timeout=REDIS_OP_TIMEOUT_SECONDS)

async def redis_ready() -> bool:
    """
    True if Redis should be used for this request.
    Pings Redis on first use and again once the failure cooldown has passed.
    """
    if not redis_client:
        return False
    if redis_healthy:
        return True
    if redis_healthy is False and time.monotonic() - redis_last_failure_at < REDIS_FAILURE_COOLDOWN_SECONDS:
        return False
    try:
        await redis_call(redis_client.ping())
        mark_redis_success()
        return True
    except Exception as e:
        mark_redis_failure("health check", e)
        return False

async def current_store_mode() -> str:
    return "redis" if await redis_ready() else "memory"

# Pydantic models
class InitiateSessionRequest(BaseModel):
    username: str = Field(max_length=MAX_USERNAME_LENGTH)

class InitiateSessionResponse(BaseModel):
    session_id: str
    message: str
    username: str

class QueryRequest(BaseModel):
    message: str = Field(max_length=MAX_MESSAGE_LENGTH)

class QueryResponse(BaseModel):
    response: str
    session_id: str
    username: str

class ChatMessage(BaseModel):
    role: str
    content: str

class AddPromptRequest(BaseModel):
    additional_prompt: str = Field(max_length=MAX_ADDITIONAL_PROMPT_LENGTH)
    # Signature returned by an earlier PIN-approved save of the same text.
    signature: Optional[str] = Field(default=None, max_length=128)

class AddPromptResponse(BaseModel):
    message: str
    session_id: str
    additional_prompt: str
    # Present when the grown-up PIN is enabled. Send it back with the same
    # text to apply the instructions to a new session without the PIN.
    signature: Optional[str] = None

class ParentStatusResponse(BaseModel):
    pin_required: bool

class ParentVerifyRequest(BaseModel):
    pin: str = Field(max_length=64)

class ParentVerifyResponse(BaseModel):
    parent_token: str
    expires_in: int

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

def session_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"

def utc_now() -> datetime:
    return datetime.utcnow()

def serialize_session(session_data: Dict[str, Any]) -> str:
    payload = dict(session_data)
    for field in ("created_at", "last_activity"):
        if isinstance(payload.get(field), datetime):
            payload[field] = payload[field].isoformat()
    return json.dumps(payload)

def deserialize_session(raw_session: Any) -> Optional[Dict[str, Any]]:
    if not raw_session:
        return None

    if isinstance(raw_session, dict):
        session_data = raw_session
    else:
        session_data = json.loads(raw_session)

    for field in ("created_at", "last_activity"):
        if isinstance(session_data.get(field), str):
            session_data[field] = datetime.fromisoformat(session_data[field])
    return session_data

def memory_session_expired(session_data: Dict[str, Any]) -> bool:
    return session_data["last_activity"] < utc_now() - timedelta(seconds=SESSION_TTL_SECONDS)

def prune_memory_sessions():
    expired_session_ids = [
        session_id for session_id, session_data in sessions.items()
        if memory_session_expired(session_data)
    ]
    for session_id in expired_session_ids:
        sessions.pop(session_id, None)

def get_memory_session(session_id: str, refresh_ttl: bool = False) -> Optional[Dict[str, Any]]:
    session_data = sessions.get(session_id)
    if not session_data:
        return None
    if memory_session_expired(session_data):
        sessions.pop(session_id, None)
        return None
    if refresh_ttl:
        session_data["last_activity"] = utc_now()
    return session_data

async def prune_expired_session_index():
    """Best-effort cleanup. Never raises."""
    prune_memory_sessions()

    if not await redis_ready():
        return
    expires_before = int((utc_now() - timedelta(seconds=SESSION_TTL_SECONDS)).timestamp())
    try:
        await redis_call(redis_client.zremrangebyscore(SESSION_INDEX_KEY, 0, expires_before))
        mark_redis_success()
    except Exception as e:
        mark_redis_failure("prune", e)

async def save_session(session_id: str, session_data: Dict[str, Any]):
    session_data["last_activity"] = utc_now()

    if await redis_ready():
        try:
            serialized = serialize_session(session_data)
            await redis_call(redis_client.set(session_key(session_id), serialized, ex=SESSION_TTL_SECONDS))
            await redis_call(redis_client.zadd(SESSION_INDEX_KEY, {session_id: int(session_data["last_activity"].timestamp())}))
            mark_redis_success()
            # Session now lives in Redis; drop any copy made while Redis was down.
            sessions.pop(session_id, None)
            return
        except Exception as e:
            mark_redis_failure("save_session", e)

    sessions[session_id] = session_data

async def get_session(session_id: str, refresh_ttl: bool = False) -> Optional[Dict[str, Any]]:
    if await redis_ready():
        try:
            raw_session = await redis_call(redis_client.get(session_key(session_id)))
            mark_redis_success()
        except Exception as e:
            mark_redis_failure("get_session", e)
            raw_session = None
        else:
            try:
                session_data = deserialize_session(raw_session)
            except (ValueError, TypeError) as e:
                logger.warning(f"Stored session {session_id[:8]}... is unreadable ({type(e).__name__})")
                session_data = None
            if session_data:
                if refresh_ttl:
                    await save_session(session_id, session_data)
                return session_data

    # Not in Redis (or Redis is down): the session may have been created in
    # memory during an outage on this instance.
    return get_memory_session(session_id, refresh_ttl=refresh_ttl)

async def delete_session(session_id: str):
    sessions.pop(session_id, None)

    if not await redis_ready():
        return
    try:
        await redis_call(redis_client.delete(session_key(session_id)))
        await redis_call(redis_client.zrem(SESSION_INDEX_KEY, session_id))
        mark_redis_success()
    except Exception as e:
        mark_redis_failure("delete_session", e)

async def count_active_sessions() -> int:
    if await redis_ready():
        try:
            count = await redis_call(redis_client.zcard(SESSION_INDEX_KEY))
            mark_redis_success()
            return int(count) + len(sessions)
        except Exception as e:
            mark_redis_failure("count_active_sessions", e)
    return len(sessions)

# Counters for rate limits and PIN lockouts. Stored in Redis when available
# (shared by all instances), otherwise in memory on this instance.
COUNTER_KEY_PREFIX = "counter:"
MAX_MEMORY_COUNTERS = 10000
memory_counters: Dict[str, tuple] = {}  # key -> (count, resets_at monotonic time)

def prune_memory_counters():
    now = time.monotonic()
    for key in [k for k, (_, resets_at) in memory_counters.items() if resets_at <= now]:
        memory_counters.pop(key, None)

async def increment_counter(name: str, window_seconds: int) -> int:
    """Add one to a counter that resets window_seconds after its first hit. Returns the new count."""
    key = f"{COUNTER_KEY_PREFIX}{name}"
    if await redis_ready():
        try:
            count = int(await redis_call(redis_client.incr(key)))
            if count == 1:
                await redis_call(redis_client.expire(key, window_seconds))
            mark_redis_success()
            return count
        except Exception as e:
            mark_redis_failure("increment_counter", e)

    now = time.monotonic()
    count, resets_at = memory_counters.get(key, (0, now + window_seconds))
    if resets_at <= now:
        count, resets_at = 0, now + window_seconds
    memory_counters[key] = (count + 1, resets_at)
    if len(memory_counters) > MAX_MEMORY_COUNTERS:
        prune_memory_counters()
    return count + 1

async def read_counter(name: str) -> int:
    key = f"{COUNTER_KEY_PREFIX}{name}"
    if await redis_ready():
        try:
            value = await redis_call(redis_client.get(key))
            mark_redis_success()
            return int(value or 0)
        except Exception as e:
            mark_redis_failure("read_counter", e)

    count, resets_at = memory_counters.get(key, (0, 0))
    return count if resets_at > time.monotonic() else 0

async def reset_counter(name: str):
    key = f"{COUNTER_KEY_PREFIX}{name}"
    memory_counters.pop(key, None)
    if await redis_ready():
        try:
            await redis_call(redis_client.delete(key))
            mark_redis_success()
        except Exception as e:
            mark_redis_failure("reset_counter", e)

async def enforce_query_rate_limit(session_id: str):
    if QUERY_RATE_LIMIT_PER_MINUTE <= 0:
        return
    count = await increment_counter(f"query:{session_id}", 60)
    if count > QUERY_RATE_LIMIT_PER_MINUTE:
        logger.warning(f"Rate limit hit for session {session_id[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many messages. Please slow down a little."
        )

# Grown-up PIN helpers
def sign_value(purpose: str, value: str) -> str:
    return hmac.new(parent_signing_key, f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()

def same_secret(given: Optional[str], expected: str) -> bool:
    """Constant-time comparison that also copes with non-ASCII input."""
    if given is None:
        return False
    return hmac.compare_digest(given.encode("utf-8", "surrogatepass"), expected.encode())

def create_parent_token() -> str:
    expires_at = str(int(time.time()) + PARENT_TOKEN_TTL_SECONDS)
    return f"{expires_at}.{sign_value('parent-token', expires_at)}"

def is_valid_parent_token(token: Optional[str]) -> bool:
    if not parent_signing_key or not token:
        return False
    expires_at, _, signature = token.partition(".")
    if not expires_at.isdigit() or not signature:
        return False
    if int(expires_at) < time.time():
        return False
    return same_secret(signature, sign_value("parent-token", expires_at))

def sign_instructions(text: str) -> str:
    return sign_value("instructions", text)

def client_address(request: Request) -> str:
    # Hosting platforms (Vercel, App Runner) put the caller's address first.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# Session management
async def create_session(username: str, additional_prompt: str = None) -> str:
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
    
    session_data = {
        "username": username,
        "created_at": utc_now(),
        "last_activity": utc_now(),
        "additional_prompt": additional_prompt,
        "messages": [
            {
                "role": "system",
                "content": combined_prompt
            }
        ]
    }

    await save_session(session_id, session_data)
    
    logger.info(f"Session {session_id[:8]}... created successfully")
    return session_id

async def validate_session(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Validate session token"""
    session_id = credentials.credentials
    
    session_data = await get_session(session_id, refresh_ttl=True)
    if not session_data:
        logger.warning(f"Invalid session ID attempted: {session_id[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session ID"
        )
    logger.debug(f"Session validated and activity updated: {session_id[:8]}...")
    
    return session_id

async def cleanup_expired_sessions():
    """Clean up sessions older than 24 hours. Best-effort: never blocks a request."""
    try:
        await prune_expired_session_index()
        logger.debug("Session cleanup complete")
    except Exception as e:
        logger.warning(f"Session cleanup skipped ({type(e).__name__})")

# Query handling shared by /query and /query/stream
SAFE_REPLACEMENT_MESSAGE = "I want to make sure I'm being helpful and appropriate. Let me think of a better way to answer that! What else would you like to know? 😊"
NO_CLIENT_MESSAGE = "Oops! I'm having a little trouble right now. Can you try again later? 🤖"
AI_ERROR_MESSAGE = "Oops! I'm having a little trouble right now. Can you try asking me something else? 🤖"

async def start_query(session_id: str, message: str):
    """
    Validate the request, apply the rate limit and input filter, and add the
    child's message to the history.
    Returns (session_data, username, canned_reply). canned_reply is set when the
    AI should not be called (filtered input or no OpenAI client).
    """
    if not message.strip():
        logger.warning(f"Empty message provided in query request for session: {session_id[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty"
        )

    await enforce_query_rate_limit(session_id)

    session_data = await get_session(session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session ID"
        )

    username = session_data["username"]
    logger.info(f"Processing query for user {username} (session: {session_id[:8]}...): {message[:50]}...")

    # The message is kept in history for context even when it is filtered,
    # but filtered messages are never sent to OpenAI.
    session_data["messages"].append({"role": "user", "content": message})

    if contains_inappropriate_content(message):
        logger.warning(f"Inappropriate content detected from user {username}: {message[:30]}...")
        return session_data, username, get_kid_friendly_response()

    if not client:
        logger.error("OpenAI client is not initialized")
        return session_data, username, NO_CLIENT_MESSAGE

    return session_data, username, None

async def finish_query(session_id: str, session_data: Dict[str, Any], reply: str):
    session_data["messages"].append({"role": "assistant", "content": reply})
    await save_session(session_id, session_data)

def checked_reply(username: str, reply: Optional[str]) -> str:
    """Final safety check on a complete AI reply."""
    if not reply or not reply.strip():
        return AI_ERROR_MESSAGE
    if contains_inappropriate_content(reply):
        logger.warning(f"Inappropriate content detected in AI response for user {username}")
        return SAFE_REPLACEMENT_MESSAGE
    return reply

# A sentence ends at . ! ? or … followed by whitespace, or at a line break.
SENTENCE_END = re.compile(r"[.!?…](?=\s)|\n")

def safe_stream_boundary(text: str) -> int:
    """
    Length of the part of text made of complete sentences. Streaming only sends
    complete sentences, so the word filter never sees half a word and a child
    never sees a blocked word before the reply is replaced.
    """
    boundary = 0
    for match in SENTENCE_END.finditer(text):
        boundary = match.end()
    return boundary

def sse_event(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint with kid-friendly message"""
    return {
        "message": "Welcome to Kiddy Chat API! 🌟 A safe and fun place to chat with AI! 🤖",
        "status": "Ready for awesome conversations!",
        "version": app_version,
        "openai_api_key_status": "configured" if api_key else "missing",
        "openai_client_status": "initialized" if client else "failed",
        "session_store": await current_store_mode()
    }

@app.get("/cron/keepalive", include_in_schema=False)
async def cron_keepalive(authorization: Optional[str] = Header(default=None)):
    """
    Daily Vercel cron. Touches Redis so Upstash doesn't archive the free DB
    for inactivity. Vercel sends "Authorization: Bearer <CRON_SECRET>".
    """
    cron_secret = os.getenv("CRON_SECRET")
    if not cron_secret or not hmac.compare_digest(
        (authorization or "").encode(), f"Bearer {cron_secret}".encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    if not redis_client:
        logger.warning("Keepalive: Redis is not configured")
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"ok": False})

    # Always try, even during the failure cooldown: this is the call that keeps the DB alive.
    try:
        await redis_call(redis_client.set(KEEPALIVE_KEY, utc_now().isoformat(), ex=KEEPALIVE_TTL_SECONDS))
        mark_redis_success()
        logger.info("Keepalive: Redis OK")
        return {"ok": True}
    except Exception as e:
        mark_redis_failure("keepalive", e)
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"ok": False})

@app.get("/redoc", include_in_schema=False)
async def redoc_docs():
    """Serve ReDoc with a pinned asset URL instead of FastAPI's moving @next default."""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.redoc.ly/redoc/v2.0.0/bundles/redoc.standalone.js",
    )

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
    await cleanup_expired_sessions()
    
    # Create new session
    session_id = await create_session(request.username)
    
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
    session_data, username, reply = await start_query(session_id, request.message)

    if reply is None:
        try:
            logger.info(f"Sending request to OpenAI for user {username}")
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=session_data["messages"],
                max_completion_tokens=MAX_COMPLETION_TOKENS,
            )
            reply = checked_reply(username, response.choices[0].message.content)
            logger.info(f"Received response from OpenAI for user {username}: {reply[:50]}...")
        except Exception as e:
            logger.error(f"Error processing OpenAI request for user {username}: {str(e)}")
            reply = AI_ERROR_MESSAGE

    await finish_query(session_id, session_data, reply)

    return QueryResponse(
        response=reply,
        session_id=session_id,
        username=username
    )

@app.post("/query/stream")
async def query_stream(request: QueryRequest, session_id: str = Depends(validate_session)):
    """
    Like /query, but streams the reply as Server-Sent Events:
    - `delta` events carry {"text": ...} with the next complete sentences
    - one final `done` event carries {"response", "session_id", "username"}

    The `done` response is the reply to keep. It can differ from the deltas
    when the safety check replaced the reply, so clients should show it.
    """
    session_data, username, canned_reply = await start_query(session_id, request.message)

    async def events():
        reply = canned_reply
        if reply is None:
            full_text = ""
            sent = 0
            blocked = False
            stream = None
            try:
                logger.info(f"Streaming request to OpenAI for user {username}")
                stream = await client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=session_data["messages"],
                    max_completion_tokens=MAX_COMPLETION_TOKENS,
                    stream=True,
                )
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content
                    if not delta:
                        continue
                    full_text += delta
                    boundary = safe_stream_boundary(full_text)
                    if boundary > sent:
                        if contains_inappropriate_content(full_text[:boundary]):
                            blocked = True
                            break
                        yield sse_event("delta", {"text": full_text[sent:boundary]})
                        sent = boundary
                reply = SAFE_REPLACEMENT_MESSAGE if blocked else checked_reply(username, full_text)
                if blocked:
                    logger.warning(f"Inappropriate content detected in streamed AI response for user {username}")
            except Exception as e:
                logger.error(f"Error streaming OpenAI request for user {username}: {str(e)}")
                reply = AI_ERROR_MESSAGE
            finally:
                if stream is not None:
                    try:
                        await stream.close()
                    except Exception:
                        pass

        await finish_query(session_id, session_data, reply)
        yield sse_event("done", {"response": reply, "session_id": session_id, "username": username})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str, auth_session_id: str = Depends(validate_session)):
    """
    Get chat history for a session
    """
    if session_id != auth_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session ID"
        )

    session_data = await get_session(auth_session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session ID"
        )
    
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
    session_data = await get_session(session_id)
    username = session_data["username"] if session_data else "unknown"
    await delete_session(session_id)
    
    logger.info(f"Session ended for user {username}. Session ID: {session_id[:8]}...")
    
    return {
        "message": f"Session ended successfully for {username}",
        "session_id": session_id
    }

@app.get("/sessions/active")
async def get_active_sessions():
    """
    Get count of active sessions (for monitoring)
    """
    await cleanup_expired_sessions()
    active_sessions = await count_active_sessions()

    return {
        "active_sessions": active_sessions
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

@app.get("/parent/status", response_model=ParentStatusResponse)
async def parent_status():
    """
    Whether a grown-up PIN is needed to change session instructions
    """
    return ParentStatusResponse(pin_required=parent_pin is not None)

@app.post("/parent/verify", response_model=ParentVerifyResponse)
async def verify_parent_pin(body: ParentVerifyRequest, request: Request):
    """
    Check the grown-up PIN and return a short-lived parent token.
    Send it as the X-Parent-Token header to /session/add-prompt.
    Too many wrong PINs lock verification for a while (HTTP 429).
    """
    if not parent_pin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No grown-up PIN is configured"
        )

    client_key = f"pin-fail:{client_address(request)}"
    total_key = "pin-fail:all"
    if (
        await read_counter(client_key) >= PIN_MAX_FAILURES_PER_CLIENT
        or await read_counter(total_key) >= PIN_MAX_FAILURES_TOTAL
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many wrong PINs. Please try again later."
        )

    if not same_secret(body.pin.strip(), parent_pin):
        await increment_counter(client_key, PIN_LOCKOUT_SECONDS)
        await increment_counter(total_key, PIN_LOCKOUT_SECONDS)
        logger.warning("Wrong grown-up PIN entered")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong PIN"
        )

    await reset_counter(client_key)
    return ParentVerifyResponse(
        parent_token=create_parent_token(),
        expires_in=PARENT_TOKEN_TTL_SECONDS
    )

@app.post("/session/add-prompt", response_model=AddPromptResponse)
async def add_session_prompt(
    request: AddPromptRequest,
    session_id: str = Depends(validate_session),
    x_parent_token: Optional[str] = Header(default=None),
):
    """
    Add an additional prompt to the current session (appends to default prompt)
    This allows frontend to customize behavior without overwriting safety defaults

    When PARENT_PIN is set, this also needs either an X-Parent-Token header from
    /parent/verify, or the `signature` returned by an earlier approved save of
    the same text (so saved instructions can be applied to new sessions).
    """
    additional_prompt = request.additional_prompt.strip()
    if not additional_prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Additional prompt cannot be empty"
        )

    signature = None
    if parent_pin:
        signature = sign_instructions(additional_prompt)
        approved = is_valid_parent_token(x_parent_token) or same_secret(request.signature, signature)
        if not approved:
            logger.warning(f"Unapproved instructions change rejected for session {session_id[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A grown-up PIN is needed to change the instructions"
            )

    session_data = await get_session(session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session ID"
        )

    # Update the additional prompt for this session
    session_data["additional_prompt"] = additional_prompt

    # Rebuild the system prompt with the additional instruction
    base_prompt = get_kids_system_prompt()
    combined_prompt = f"{base_prompt}\n\nAdditional instructions for this session: {additional_prompt}"

    # Update the system message in the conversation history
    if session_data["messages"] and session_data["messages"][0]["role"] == "system":
        session_data["messages"][0]["content"] = combined_prompt
    else:
        # If no system message exists, add one at the beginning
        session_data["messages"].insert(0, {
            "role": "system",
            "content": combined_prompt
        })

    await save_session(session_id, session_data)

    return AddPromptResponse(
        message="Additional prompt added successfully! This will guide our conversation while keeping all safety features active.",
        session_id=session_id,
        additional_prompt=additional_prompt,
        signature=signature
    )

@app.get("/session/prompt-info")
async def get_session_prompt_info(session_id: str = Depends(validate_session)):
    """
    Get the current session's prompt information including any additional prompts
    """
    session_data = await get_session(session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session ID"
        )
    
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
